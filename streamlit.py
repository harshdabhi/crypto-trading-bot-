import streamlit as st  

st.set_page_config(
    layout="wide", 
    page_title="Crypto Trading Bot",
    page_icon=":bar_chart:",
    )

st.title("Crypto Trading Bot")




############################################ code logic goes here ############################################




# Print the fetched data





# Print the fetched data

pswd=st.text_input(label="pass",type="password")
print(pswd)

start=st.button("Start Trading!")

if start:
    stop=False
    
    st.write('execution has started')

stop=st.button("Stop Trading!")


if stop:
    print('execution has stopped')


st.image('./images/plot.png')

