import streamlit as st
from string_data_processor import StringDataProcessor

st.set_page_config(page_title="Week 3: TDD Processor", layout="centered")
st.title("🧪 Week 3: Automated Testing & Text Processor")

raw_text = st.text_area("Input Raw Text:", "  Python   is   fast! python is modular.  ")
raw_numbers = st.text_input("Delimited Numbers:", "10.5, 20.0, 30.5, 40.0")

if st.button("Process Data"):
    clean = StringDataProcessor.sanitize_whitespace(raw_text)
    freq = StringDataProcessor.extract_word_frequencies(raw_text)
    nums = StringDataProcessor.parse_delimited_numbers(raw_numbers)
    
    st.write("**Sanitized String:**", clean)
    st.write("**Word Frequencies:**", freq)
    st.write("**Parsed Numeric Array:**", nums)
    st.metric("Total Sum", sum(nums))
