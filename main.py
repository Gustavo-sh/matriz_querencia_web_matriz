import pyodbc
from datetime import datetime
from telegram_config import notify_telegram
from utils import write_log

CONNECTION_STRING = "Driver={ODBC Driver 18 for SQL Server};Server=primno4;Database=Robbyson;Trusted_Connection=yes;TrustServerCertificate=yes;"

query_write = f"""
SET NOCOUNT ON
if object_id('tempdb..#hmn') is not null drop table #hmn;

-- geração da temp do homminum
;with cte_hmn_1 as (
    select distinct
        atributo,
        case
            when gerentesenior is not null then gerentesenior
            when gerentepleno is not null then gerentepleno
            when gerente is not null then gerente
            else ''
        end as gerente,
        gerente_executivo,
        row_number() over (partition by atributo order by gerente) as rn -- row number para pegar apenas o primeiro gerente alfabeticamente para os atributos que contém mais de um
    from robbyson.rlt.hmn (nolock)
    where --data = dateadd(d, 1, eomonth(getdate(), @indice)) -- modificado em 04/02/2026 para a data d-1 em vez da data do mes em questão para evitar problemas com atributos que não aparecem na pagina apoio
    data = convert(date, getdate()-1)
    and situacaohominum in ('ativo', 'treinamento')
    and tipohierarquia = 'operação'
    and nivelhierarquico = 'operacional'
    and funcaorm not like 'auxiliar%'
    and funcaorm not like 'analista%'
    and atributo is not null
    and atributo not like '%salario_funcao%'

)

select atributo, gerente, GERENTE_EXECUTIVO
into #hmn
from cte_hmn_1
where rn = 1

-- matriz querencia para atributos válidos no hominum que não estão na sistema matriz no mes atual
; with  atributos_validos as (
    select distinct 
        matricula,
        atributo
    from robbyson.rlt.hmn (nolock) 
    where data = convert(date, getdate()-1)
        and situacaohominum in ('ativo')
        and tipohierarquia = 'operação'
        and nivelhierarquico = 'operacional'
        and funcaorm not like 'auxiliar%'
        and funcaorm not like 'analista%'
        and atributo is not null
        and atributo not like '%salario_funcao%'
)

, atributos_dados_disp as (
    select distinct
        atributo
    from robbyson.ext.indicadoresgeral (nolock) ind
    inner join atributos_validos av
        on av.matricula = ind.matricula
    where idindicador = 901
    and ind.data >= dateadd(day, 1, eomonth(getdate(), -1))
    and ind.data <  dateadd(day, 1, eomonth(getdate(), 0))
)

, atributos_sem_dados as (
    select distinct
        ad.atributo,
        h.gerente,
        h.gerente_executivo
    from atributos_dados_disp ad
    left join #hmn h
        on ad.atributo = h.atributo
    where not exists (
        select distinct data_inicio
        from robbyson.rby.meta (nolock) m
        where m.atributo = ad.atributo
            and m.data_inicio >= dateadd(day, 1, eomonth(getdate(), -1))
            and m.data_inicio <  dateadd(day, 1, eomonth(getdate(), 0))
    )
    and not exists (
        select 1
        from robbysonmatriz.dbo.sistema_matriz (nolock) sm
        where sm.atributo = ad.atributo
        and sm.periodo = dateadd(day,1,eomonth(getdate(),-1))
    )
)

, indicadores_padrao as (
    select *
    from (values
        ('901 - % DISPONIBILIDADE','94',35,'PERCENTUAL'),
        ('15 - TEMPO LOGADO','00:00:00',0,'HORA'),
        ('25 - NR17','00:00:00',0,'HORA'),
        ('6 - % ABSENTEÍSMO','5',0,'PERCENTUAL')
    ) v(id_nome_indicador, meta, moedas, tipo_indicador)
)

, sinonimos as (
    select * from (values 
        ('oi',  'nio'),
        ('net', 'claro'),
        ('claro', 'net')
    ) as t(clientesinonimo, termovalido)
)

, partes_extraidas AS (
    SELECT 
        atributo,
        LTRIM(RTRIM(SUBSTRING(atributo, 1, pos1 - 1))) AS cliente,
        LTRIM(RTRIM(SUBSTRING(atributo, pos1 + 3, pos2 - (pos1 + 3)))) AS produto
    FROM atributos_sem_dados
    CROSS APPLY (SELECT CHARINDEX(' - ', atributo) AS pos1) c1
    CROSS APPLY (SELECT CHARINDEX(' - ', atributo, pos1 + 3) AS pos2) c2
    WHERE pos1 > 0 AND pos2 > pos1
)

, atributos_aberracao as (
    select distinct
        p.atributo
        --p.cliente,
        --p.produto,
        --'cliente diferente do produto' as motivoinvalido
    from partes_extraidas p
    where upper(p.cliente) <> 'premium'
    and p.produto not like '%' + p.cliente + '%'
    and not exists (
        select 1 
        from sinonimos s
        where upper(s.clientesinonimo) = upper(p.cliente)
            and p.produto like '%' + s.termovalido + '%'
    )
    and UPPER(cliente) <> 'PESSOAS'
)

insert into robbysonmatriz.dbo.sistema_matriz
select
    upper(a.atributo) as atributo,
    i.id_nome_indicador,
    i.meta,
    i.moedas,
    i.tipo_indicador,
    'NAO' as acumulado,
    'DIARIO' as esquema_acumulado,
    'OPERACIONAL' as tipo_matriz,
    dateadd(d, 1, eomonth(getdate(), -1)) as data_inicio,
    eomonth(getdate(), 0) as data_fim,
    dateadd(d, 1, eomonth(getdate(), -1)) as periodo,
    '6X1' as escala,
    '{datetime.now().date()}' as descricao,
    1 as ativo,
    '' as chamado,
    upper(a.gerente) as gerente,
    'NAO' as possui_dmm,
    null as dmm,
    0 as qualidade,
    0 as da_qualidade,
    '' as data_da_qualidade,
    0 as planejamento,
    0 as da_planejamento,
    '' as data_da_planejamento,
    0 as exop,
    0 as da_exop,
    '' as data_da_exop,
    a.gerente_executivo as superintendente,
    0 as operacao,
    0 as da_operacao,
    '' as data_da_operacao,
    0 as importado,
    '' as data_importacao,
    '' as meta_apoio,
    i.meta as meta_final,
    '' as id_incluso,
    '' as id_excluso,
    1 as importacao_valida,
    0 as matriz_coletada,
    '' as justificativa_meta,
    '' as observacao_operacao,
    LTRIM(RTRIM(LEFT(i.id_nome_indicador, CHARINDEX('-', i.id_nome_indicador) - 1))) as id_indicador,
    0 as moedas_apoio
from atributos_sem_dados a
cross join indicadores_padrao i
where a.atributo not in (select atributo from atributos_aberracao)

drop table #hmn
"""

query_read = f"""
SET NOCOUNT ON
if object_id('tempdb..#hmn') is not null drop table #hmn;

-- geração da temp do homminum
;with cte_hmn_1 as (
    select distinct
        atributo,
        case
            when gerentesenior is not null then gerentesenior
            when gerentepleno is not null then gerentepleno
            when gerente is not null then gerente
            else ''
        end as gerente,
        gerente_executivo,
        row_number() over (partition by atributo order by gerente) as rn -- row number para pegar apenas o primeiro gerente alfabeticamente para os atributos que contém mais de um
    from robbyson.rlt.hmn (nolock)
    where --data = dateadd(d, 1, eomonth(getdate(), @indice)) -- modificado em 04/02/2026 para a data d-1 em vez da data do mes em questão para evitar problemas com atributos que não aparecem na pagina apoio
    data = convert(date, getdate()-1)
    and situacaohominum in ('ativo', 'treinamento')
    and tipohierarquia = 'operação'
    and nivelhierarquico = 'operacional'
    and funcaorm not like 'auxiliar%'
    and funcaorm not like 'analista%'
    and atributo is not null
    and atributo not like '%salario_funcao%'

)

select atributo, gerente, GERENTE_EXECUTIVO
into #hmn
from cte_hmn_1
where rn = 1

; with  atributos_validos as (
    select distinct 
        matricula,
        atributo
    from robbyson.rlt.hmn (nolock) 
    where data = convert(date, getdate()-1)
        and situacaohominum in ('ativo')
        and tipohierarquia = 'operação'
        and nivelhierarquico = 'operacional'
        and funcaorm not like 'auxiliar%'
        and funcaorm not like 'analista%'
        and atributo is not null
        and atributo not like '%salario_funcao%'
)

, atributos_dados_disp as (
    select distinct
        atributo
    from robbyson.ext.indicadoresgeral (nolock) ind
    inner join atributos_validos av
        on av.matricula = ind.matricula
    where idindicador = 901
    and ind.data >= dateadd(day, 1, eomonth(getdate(), -1))
    and ind.data <  dateadd(day, 1, eomonth(getdate(), 0))
)

, atributos_sem_dados as (
    select distinct
        ad.atributo,
        h.gerente,
        h.gerente_executivo
    from atributos_dados_disp ad
    left join #hmn h
        on ad.atributo = h.atributo
    where not exists (
        select distinct data_inicio
        from robbyson.rby.meta (nolock) m
        where m.atributo = ad.atributo
            and m.data_inicio >= dateadd(day, 1, eomonth(getdate(), -1))
            and m.data_inicio <  dateadd(day, 1, eomonth(getdate(), 0))
    )
    and not exists (
        select 1
        from robbysonmatriz.dbo.sistema_matriz (nolock) sm
        where sm.atributo = ad.atributo
        and sm.periodo = dateadd(day,1,eomonth(getdate(),-1))
    )
)

, sinonimos as (
    select * from (values 
        ('oi',  'nio'),
        ('net', 'claro'),
        ('claro', 'net')
    ) as t(clientesinonimo, termovalido)
)

, partes_extraidas AS (
    SELECT 
        atributo,
        LTRIM(RTRIM(SUBSTRING(atributo, 1, pos1 - 1))) AS cliente,
        LTRIM(RTRIM(SUBSTRING(atributo, pos1 + 3, pos2 - (pos1 + 3)))) AS produto
    FROM atributos_sem_dados
    CROSS APPLY (SELECT CHARINDEX(' - ', atributo) AS pos1) c1
    CROSS APPLY (SELECT CHARINDEX(' - ', atributo, pos1 + 3) AS pos2) c2
    WHERE pos1 > 0 AND pos2 > pos1
)

, atributos_aberracao as (
    select distinct
        p.atributo
        --p.cliente,
        --p.produto,
        --'cliente diferente do produto' as motivoinvalido
    from partes_extraidas p
    where upper(p.cliente) <> 'premium'
    and p.produto not like '%' + p.cliente + '%'
    and not exists (
        select 1 
        from sinonimos s
        where upper(s.clientesinonimo) = upper(p.cliente)
            and p.produto like '%' + s.termovalido + '%'
    )
    and UPPER(cliente) <> 'PESSOAS'
)

select distinct atributo from atributos_sem_dados where atributo not in (select atributo from atributos_aberracao)
"""

def exec_query(conn):
    try:
        results = None
        cur = conn.cursor()
        cur.execute(query_read)
        results = [row[0] for row in cur.fetchall()]
        if results:
            cur.execute(query_write)
        conn.commit()
        return results
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        try:
            cur.close()
        except:
            pass

if __name__ == "__main__":
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        attributes = exec_query(conn)
        if not attributes:
            notify_telegram("🚫 Nenhum atributo sem matriz no mes atual, com hc ativo e com dados para disponibilidade encontrado para cadastro de matriz querencia.")
            write_log("Nenhum atributo sem matriz no mes atual, com hc ativo e com dados para disponibilidade encontrado para cadastro de matriz querencia.")
        else:
            notify_telegram("✅ Atributos cadastrados com matriz querencia para o mes atual (importação valida = 0): \n\n" + str(attributes))
            write_log("Atributos cadastrados com matriz querencia para o mes atual (importação valida = 0): \n\n" + str(attributes))
        conn.close()
    except Exception as e:
        notify_telegram("⚠️ Erro no cadastro automático de matriz querência: " + str(e))
        write_log("Erro no cadastro automático de matriz querência: " + str(e))
    finally:
        try:
            conn.close()
        except:
            pass