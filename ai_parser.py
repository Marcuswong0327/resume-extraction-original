import requests
import json
import streamlit as st
import time

class AIParser:
    """Handle Claude Sonnet 4 API integration via OpenRouter for intelligent resume parsing"""
    
    def __init__(self, api_key):

        if not api_key:
            raise ValueError("OpenRouter API key is required")
            
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Resume Parser"
        }
        
        # Test the API connection
        self._test_connection()
    
    def _test_connection(self):

        try:
            test_payload = {
                "model": "anthropic/claude-sonnet-4",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"API test failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"OpenRouter API connection test failed: {str(e)}")
    
    def parse_resume(self, resume_text):

        try:
            if not resume_text or not resume_text.strip():
                return self._create_empty_structure()
            
            # Create prompt 
            prompt = self._create_parsing_prompt(resume_text)
            
            # Make API call 
            response = self._make_api_call_with_retry(prompt)
            
            if response:
                return self._parse_api_response(response)
            else:
                return self._create_empty_structure()
                
        except Exception as e:
            st.error(f"Error parsing resume with AI: {str(e)}")
            return self._create_empty_structure()
    
    def _create_parsing_prompt(self, resume_text):
 
        # Truncate text if too long to avoid token limits
        max_chars = 15000
        if len(resume_text) > max_chars:
            resume_text = resume_text[:max_chars] + "..."
        
        prompt = f"""
You are an expert resume parser. Analyze the following resume text and extract structured information in JSON format.

Resume Text:
{resume_text}

Please extract and return ONLY a valid JSON object with the following structure:
sometimes the information maybe on second page. but majority is first page. 
{{
    "first name": "candidate first name, normally on top few lines of first pages",
    "last name": "candidate last name, normallly on top few lines of first page",
    "mobile": "phone/mobile number, near around name area",
    "email": "email address, near around mobile phone number area",
    "current job title": "current/most recent job title based on latest date, normally the most recent job title will be listed on first",
    "current company": "current/most recent company name",
    "previous job title": "previous job title (before current one), based on the date, normally second job title is before current one",
    "previous company": "previous company name (before current one)"
}}

Instructions for determining current vs previous positions:
1. Look for dates in the work experience section
2. The position with the most recent dates (or "present", "current", "Now" etc.) is the CURRENT position
3. The position immediately before the current one (chronologically) is the PREVIOUS position
4. If only one job is mentioned, put it as current and leave previous fields as empty
5. Pay attention to date formats like "2020-present", "Jan 2023 - Current", "2022-2024", etc.

Rules:
1. Return ONLY valid JSON, no additional text or explanations
2. If information is not found, use empty string ""
3. Be very careful with dates to correctly identify current vs previous positions
4. Extract full names and split into first name and last name
5. Look for mobile/phone numbers in various formats
6. Be thorough and accurate in extraction
"""
        return prompt
    
    def _make_api_call_with_retry(self, prompt, max_retries=3):

        for attempt in range(max_retries):
            try:
                response = self._make_api_call(prompt)
                if response:
                    return response
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    st.error(f"OpenRouter API failed after {max_retries} attempts: {str(e)}")
                    return None
                else:
                    st.warning(f"OpenRouter API attempt {attempt + 1} failed, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def _make_api_call(self, prompt):

        try:
            payload = {
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1,
                "stream": False
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60  
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
            else:
                error_msg = f"Claude API error: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            raise Exception("Claude API request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error calling Claude API: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling Claude API: {str(e)}")
    
    def _parse_api_response(self, response_text):

        try:
            # Try to find JSON in the response
            response_text = response_text.strip()
            
            # Remove any markdown code block markers
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
                
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Try to find JSON object in the text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx + 1]
                parsed_data = json.loads(json_text)
            else:
                # Try parsing the entire text
                parsed_data = json.loads(response_text)
            
            # Validate structure
            return self._validate_parsed_data(parsed_data)
            
        except json.JSONDecodeError as e:
            st.warning(f"Failed to parse AI response as JSON: {str(e)}")
            st.text("Raw response:")
            st.code(response_text)
            return self._create_empty_structure()
        except Exception as e:
            st.warning(f"Error processing AI response: {str(e)}")
            return self._create_empty_structure()
    
    def _validate_parsed_data(self, data):
        
        # Ensure all required fields exist
        validated_data = {
            "first name": str(data.get("first name", "")).strip(),
            "last name": str(data.get("last name", "")).strip(),
            "mobile": str(data.get("mobile", "")).strip(),
            "email": str(data.get("email", "")).strip(),
            "current job title": str(data.get("current job title", "")).strip(),
            "current company": str(data.get("current company", "")).strip(),
            "previous job title": str(data.get("previous job title", "")).strip(),
            "previous company": str(data.get("previous company", "")).strip()
        }
        
        return validated_data
    
    def _create_empty_structure(self):
        
        return {
            "first name": "",
            "last name": "",
            "mobile": "",
            "email": "",
            "current job title": "",
            "current company": "",
            "previous job title": "",
            "previous company": ""
        }
