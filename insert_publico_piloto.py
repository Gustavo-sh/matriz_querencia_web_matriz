import pyodbc
from datetime import datetime
from telegram_config import notify_telegram

CONNECTION_STRING = "Driver={ODBC Driver 18 for SQL Server};Server=primno4;Database=RobbysonMatriz;Trusted_Connection=yes;TrustServerCertificate=yes;"

def insert_publico_piloto():
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            insert into robbysonmatriz.dbo.publico_piloto_sistema_matriz
            SELECT distinct
                a.atributo, '', '', '', cast(getdate() as date)
            from robbysonmatriz.dbo.hmn (nolock) h
            left join robbysonmatriz.dbo.atributo (nolock) a on h.atributo = a.atributo
            where produto in (select distinct produto from robbyson.dbo.produtos_piloto_sistema_matriz (nolock))
            and situacaohominum in ('ativo', 'treinamento')
            and tipohierarquia = 'operação'
            and nivelhierarquico = 'operacional'
            and funcaorm not like 'auxiliar%'
            and funcaorm not like 'analista%'
            and a.atributo is not null
            and not exists (
                select 1 from robbysonmatriz.dbo.publico_piloto_sistema_matriz pp (nolock)
                where pp.atributo = h.atributo
            )
            and not exists (
                select 1 from robbysonmatriz.dbo.atributos_sem_matriz asm (nolock)
                where asm.atributo = h.atributo
            )
        """)
        conn.commit()
        cursor.close()
    notify_telegram(f"✅ Matriz Querência - Publico Piloto foi atualizado com sucesso!")

if __name__ == "__main__":
    insert_publico_piloto()