import streamlit as st
import pandas as pd
import json
import traceback
from pdf_processor import PDFProcessor
from word_processor import WordProcessor
from ai_parser import AIParser
from excel_exporter import ExcelExporter
import base64

def main():
    st.set_page_config(
        page_title="Resume Parser 2.0",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Resume Parser 2.0")
    st.title("💰Road to Million Biller!!!")

    
    # Initialize session state
    if 'processed_candidates' not in st.session_state:
        st.session_state.processed_candidates = []
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'processing_in_progress' not in st.session_state:
        st.session_state.processing_in_progress = False
    
    # Check credentials availability
    credentials_status = check_credentials()

    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload as many you like!",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully")
            
            # Display uploaded files
            with st.expander("📋 Uploaded Files", expanded=True):
                for i, file in enumerate(uploaded_files, 1):
                    file_type = file.name.split('.')[-1].upper()
                    st.write(f"{i}. {file.name} ({file.size} bytes) - {file_type}")
            
            # Process files button
            process_disabled = not credentials_status['deepseek_status'] or st.session_state.processing_in_progress
            
            if st.button("Process Resumes", type="primary", use_container_width=True, disabled=process_disabled):
                if not credentials_status['deepseek_status']:
                    st.error("Please configure OpenRouter API credentials before processing.")
                else:
                    process_resumes(uploaded_files)
    
    with col2:
        st.image("linktal logo transparent copy.png", width = 350)
        st.header("Processing Status")
        
        if st.session_state.processing_in_progress:
            st.info("Processing")
        elif st.session_state.processed_candidates:
            st.metric("Processed Candidates", len(st.session_state.processed_candidates))
            
            if st.session_state.processing_complete:
                st.success("Processed successfully!")

                if st.button("Download Excel Report", type = "secondary",use_container_width=True):
                    generate_and_download_excel()
            else:
                st.info("No candidates processed yet.")
     
    
    # Display processed candidates
    if st.session_state.processed_candidates:
        st.header("Processed Candidates")
        
        # Create DataFrame for display
        display_data = []
        for candidate in st.session_state.processed_candidates:
            display_data.append({
                'First Name': candidate.get('first name', ''),
                'Last Name': candidate.get('last name', ''),
                'Mobile': candidate.get('mobile', ''),
                'Email': candidate.get('email', ''),
                'Current Job Title': candidate.get('current job title', ''),
                'Current Company': candidate.get('current company', ''),
                'Previous Job Title': candidate.get('previous job title', ''),
                'Previous Company': candidate.get('previous company', ''),
                'Source File': candidate.get('filename', '')
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True)

def check_credentials():
    deepseek_status = False
    
    try:
        # Check OpenRouter API key
        if "DEEPSEEK_API_KEY" in st.secrets:
            deepseek_status = True
            
    except Exception as e:
        st.error(f"Error checking credentials: {str(e)}")
    
    return {
        'deepseek_status': deepseek_status
    }

def process_resumes(uploaded_files):
    st.session_state.processing_in_progress = True
    st.session_state.processing_complete = False
    st.session_state.processed_candidates = []
    
    try:
        # Initialize services
        with st.spinner("Initializing"):
            try:
                pdf_processor = PDFProcessor()
                word_processor = WordProcessor()
                ai_parser = AIParser(st.secrets["DEEPSEEK_API_KEY"])
            except Exception as e:
                st.error(f"Error initializing services: {str(e)}")
                st.session_state.processing_in_progress = False
                return
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        total_files = len(uploaded_files)
        successful_processes = 0
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                current_progress = (i / total_files)
                progress_bar.progress(current_progress)
                status_text.text(f"Processing {uploaded_file.name}... ({i+1}/{total_files})")
                
                # Extract text based on file type
                file_extension = uploaded_file.name.lower().split('.')[-1]
                extracted_text = ""
                
                if file_extension == 'pdf':
                    with st.spinner(f"Extracting {uploaded_file.name}..."):
                        extracted_text = pdf_processor.process_pdf_file(uploaded_file)
                elif file_extension in ['docx']:
                    with st.spinner(f"Extracting {uploaded_file.name}..."):
                        extracted_text = word_processor.process_word_file(uploaded_file)
                else:
                    st.warning(f"Unsupported file type: {file_extension}")
                    continue
                
                if not extracted_text.strip():
                    st.warning(f"No text TO extract from {uploaded_file.name}")
                    continue
                
                # Parse resume using AI
                with st.spinner(f"Analyzing {uploaded_file.name}."):
                    parsed_data = ai_parser.parse_resume(extracted_text)
                
                # Add filename to the parsed data
                parsed_data['filename'] = uploaded_file.name
                
                # Add to results
                st.session_state.processed_candidates.append(parsed_data)
                successful_processes += 1
                
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                continue
        
        # Final progress update
        progress_bar.progress(1.0)
        
        # Mark processing as complete
        st.session_state.processing_complete = True
        st.session_state.processing_in_progress = False
        
        if successful_processes > 0:
            st.success(f"Successfully processed {successful_processes}/{total_files} resume files.")
        else:
            st.warning(" No files were successfully processed.")
            
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.session_state.processing_in_progress = False
        # Show detailed error for debugging
        with st.expander("Error Details"):
            st.code(traceback.format_exc())


def generate_and_download_excel():
    """Generate and auto-download Excel report"""
    try:
        if not st.session_state.processed_candidates:
            st.warning("No candidate data to export.")
            return

        with st.spinner("Generating Excel report..."):
            exporter = ExcelExporter()
            excel_data = exporter.export_candidates(st.session_state.processed_candidates)

            # Encode to base64 for direct download
            b64 = base64.b64encode(excel_data).decode()
            filename = "resume_analysis.xlsx"
            
            # Auto trigger download
            js = f"""
            <html>
            <head>
            <meta http-equiv="refresh" content="0; url=data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" />
            </head>
            <body>
            
            </body>
            </html>
            """
            st.components.v1.html(js, height=0)

    except Exception as e:
        st.error(f"Error generating Excel report: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()







































