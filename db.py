from sqlalchemy import create_engine
conn_str = 'mysql://root:cset155@localhost/ecomdb'
engine = create_engine(conn_str, echo=True)
conn = engine.connect()