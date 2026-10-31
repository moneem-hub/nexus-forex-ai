import pickle
import streamlit as st
from config import MODEL_FILES


@st.cache_resource
def load_model():
    for fname in MODEL_FILES:
        try:
            with open(fname, "rb") as f:
                return pickle.load(f)
        except Exception:
            continue
    return None
