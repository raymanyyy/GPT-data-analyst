import openai
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect, text

openai.api_key = st.secrets['OPENAI_API_KEY']

db_products_dict = {
    'postgres': 'postgresql+psycopg2',
}

with st.sidebar:
    with st.form(key='my_form_to_submit'):
        user_request = st.text_area("Let chatGPT to do SQL for you")

        st.write('Enter your database credentials:')
        db_type = st.selectbox('db type', db_products_dict.keys())
        db_host = st.text_input('host', 'localhost')
        db_user = st.text_input('user', 'postgres')
        db_password = st.text_input('password', 'postgres')
        db_name = st.text_input('database', 'world')
        db_port = st.text_input('port', '5432')
        submit_button = st.form_submit_button(label='Submit')

if submit_button:
    # check if the user has entered a request
    if not user_request:
        st.error('Please enter a request')
        st.stop()

    # check if the user has entered a database credentials
    if not db_host or not db_user or not db_password or not db_name or not db_port:
        st.error('Please enter a database credentials')
        st.stop()

    # try to create an engine to connect to the database
    try:
        engine = create_engine(f'{db_products_dict[db_type]}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
        inspector = inspect(engine)
    except Exception as e:
        st.error(f'Could not connect to the database. Error: {e}')
        st.stop()

    table_names = inspector.get_table_names()

    # create an empty dictionary to store the column names for each table
    column_names = {}

    # iterate through each table and get its column names
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        column_names[table_name] = [column['name'] for column in columns]

    # form an introspection doc
    doc = f"""
        DATABASE SCHEMA DOCUMENTATION\n
        Total Tables: {len(table_names)}
        """
    for table_name in table_names:
        doc += f"""
        ---
        Table Name: {table_name}\n
        Columns:
        """
        for column_name in column_names[table_name]:
            doc += f"""
            - {column_name}
            """

    intro = 'You are a helpful assistant. You will complete a task and write the results.'
    prompt = 'Given the database schema, write a SQL query that returns the following information: '
    prompt += f'{user_request}.\n'
    prompt += f'You only need to write SQL code, do not comment or explain code and do not add any additional info. \
    I need code only. Always use table name in column reference to avoid ambiguity. SQL dialect is {db_type}.\
    Only use columns and tables mentioned in the doc below. \n{doc}'

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": intro},
            {"role": "user", "content": prompt}
        ]
    )
    code = response.choices[0].message.content
    pretty_code = '```sql\n' + code + '\n```'
    code = code.replace('\n', ' ')

    with st.expander("See executed code"):
        st.write(pretty_code)
    with st.expander("See introspected BD structure"):
        st.write(doc)

    df = pd.read_sql_query(sql=text(code), con=engine.connect())

    st.write("## The results")
    st.write(df)
    st.write("Is it time to fire your Data Analysts? 😱")
