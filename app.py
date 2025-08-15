import streamlit as st
from extractor import *
from parameters import *
import logging
from Contants import *
from datetime import datetime,timedelta
import time

logging.basicConfig(
    filename=getParameter(LOGGING_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s : %(message)s"
)

st.set_page_config(layout='centered')
st.header('Extracteur de données')

countries=[]
error=False
try:
    project_id=st.text_input('ID Projet')
    Login(project_id)
    countries=getCountries()
except Exception as e:
    st.error(e)
    logging.error(str(e))
    error=True

if project_id and not error:
    begin_date=st.date_input('Date de début')
    end_date=st.date_input('Date de fin',value=begin_date+timedelta(weeks=52))
    country=st.selectbox('Choisir un pays',options=countries)
    base=st.multiselect('Base',options=['Journalier','Hebdomadaire','Mensuel'])
    btn=st.button("Télécharger les données")
    if btn and len(base)>0:
        task=extractData(country,begin_date,end_date,10,'daily' if base[0]=="Journalier" else "weekly" if base[0]=='Hebdomadaire' else "Monthly")
        st.success("🚀 Export lancé. Veuillez patienter...")
        denominator=86400 if base[0]=="daily" else 604800 if base[0]=="weekly" else 2592000
        period=math.floor((end_date-begin_date).total_seconds()/denominator)

        progress_bar = st.progress(0)
        status_text = st.empty()
        state_dict={"READY":"PRÊT","RUNNING":"EN COURS","COMPLETED":"TERMINÉ"}

        for percent_complete in range(100):
            task_status = task.status()
            state = task_status['state']
            status_text.text(f"État actuel de la tâche : {state_dict[state]}")

            if state in ['COMPLETED', 'FAILED', 'CANCELLED']:
                progress_bar.progress(100)
                break

            progress_bar.progress(percent_complete + math.floor(100/period))
            time.sleep(0.5)

        final_status = task.status()
        if final_status['state'] == 'COMPLETED':
            st.success(f"✅ Export terminé avec succès ! Vérifiez votre Google Drive > {getParameter(EXPORT_FOLDER_KEY)}")
        else:
            st.error(f"❌ Export échoué : {final_status.get('error_message', 'Erreur inconnue')}")