import logging
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path
from typing import Dict, List
import json

# Set up logging
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ResumeBuilder:
    def __init__(self):
        self.resume_data = {}
        setup_logging()

    def collect_personal_info(self, name, contact_info):
        try:
            self.resume_data['name'] = name
            self.resume_data['contact_info'] = contact_info
            logging.info('Personal info collected successfully')
        except Exception as e:
            logging.error(f'Error collecting personal info: {e}')

    def collect_experience(self, experience):
        try:
            self.resume_data['experience'] = experience
            logging.info('Experience collected successfully')
        except Exception as e:
            logging.error(f'Error collecting experience: {e}')

    def collect_education(self, education):
        try:
            self.resume_data['education'] = education
            logging.info('Education collected successfully')
        except Exception as e:
            logging.error(f'Error collecting education: {e}')

    def build_resume_text(self):
        """Build a text version of the resume"""
        try:
            resume = f"{self.resume_data['name']}\n"
            if isinstance(self.resume_data.get('contact_info'), dict):
                contact = self.resume_data['contact_info']
                resume += f"{contact.get('email', '')} | {contact.get('phone', '')} | {contact.get('location', '')}\n\n"
            resume += 'EXPERIENCE:\n'
            for exp in self.resume_data.get('experience', []):
                if isinstance(exp, dict):
                    resume += f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('dates', '')})\n"
                else:
                    resume += f"- {exp}\n"
            resume += '\nEDUCATION:\n'
            for edu in self.resume_data.get('education', []):
                if isinstance(edu, dict):
                    resume += f"- {edu.get('degree', '')} from {edu.get('institution', '')}\n"
                else:
                    resume += f"- {edu}\n"
            logging.info('Resume built successfully')
            return resume
        except Exception as e:
            logging.error(f'Error building resume: {e}')
            return 'Error building resume'

    def build_word_document(self, output_path: str, candidate_data: Dict) -> str:
        """Build a professional Word document resume"""
        try:
            doc = Document()
            
            # Set up styles
            styles = doc.styles
            
            # Header with name
            name_para = doc.add_paragraph()
            name_run = name_para.add_run(candidate_data.get('name', '').upper())
            name_run.font.size = Pt(18)
            name_run.font.bold = True
            name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Contact information
            contact = candidate_data.get('contact', {})
            contact_para = doc.add_paragraph()
            contact_text = f"{contact.get('email', '')} | {contact.get('phone', '')} | {contact.get('location', '')}"
            contact_run = contact_para.add_run(contact_text)
            contact_run.font.size = Pt(10)
            contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()  # Spacing
            
            # Professional Summary
            if candidate_data.get('professional_summary'):
                doc.add_paragraph('PROFESSIONAL SUMMARY', style='Heading 2')
                summary_para = doc.add_paragraph(candidate_data.get('professional_summary'))
                summary_para.paragraph_format.space_after = Pt(12)
            
            # Key Skills
            if candidate_data.get('key_skills'):
                doc.add_paragraph('KEY SKILLS', style='Heading 2')
                skills_para = doc.add_paragraph(', '.join(candidate_data.get('key_skills', [])))
                skills_para.paragraph_format.space_after = Pt(12)
            
            # Work Experience
            if candidate_data.get('experience'):
                doc.add_paragraph('WORK EXPERIENCE', style='Heading 2')
                for exp in candidate_data.get('experience', []):
                    # Job title and company
                    job_para = doc.add_paragraph()
                    job_run = job_para.add_run(f"{exp.get('title', '')} | {exp.get('company', '')}")
                    job_run.font.bold = True
                    job_run.font.size = Pt(12)
                    
                    # Location and dates
                    location_para = doc.add_paragraph()
                    location_run = location_para.add_run(f"{exp.get('location', '')} | {exp.get('dates', '')}")
                    location_run.font.size = Pt(10)
                    location_run.italic = True
                    
                    # Description
                    if exp.get('description'):
                        desc_para = doc.add_paragraph(exp.get('description'))
                        desc_para.paragraph_format.space_after = Pt(6)
                    
                    # Bullet points
                    for bullet in exp.get('bullets', []):
                        bullet_para = doc.add_paragraph(bullet, style='List Bullet')
                        bullet_para.paragraph_format.left_indent = Inches(0.25)
                    
                    doc.add_paragraph()  # Spacing between jobs
            
            # Education
            if candidate_data.get('education'):
                doc.add_paragraph('EDUCATION', style='Heading 2')
                for edu in candidate_data.get('education', []):
                    edu_para = doc.add_paragraph()
                    edu_text = f"{edu.get('degree', '')} in {edu.get('field', '')}"
                    edu_run = edu_para.add_run(edu_text)
                    edu_run.font.bold = True
                    
                    inst_para = doc.add_paragraph()
                    inst_run = inst_para.add_run(f"{edu.get('institution', '')} | {edu.get('graduation_year', '')}")
                    inst_run.font.size = Pt(10)
                    inst_run.italic = True
                    doc.add_paragraph()  # Spacing
            
            # Certifications
            if candidate_data.get('certifications'):
                doc.add_paragraph('CERTIFICATIONS', style='Heading 2')
                for cert in candidate_data.get('certifications', []):
                    doc.add_paragraph(cert, style='List Bullet')
                doc.add_paragraph()
            
            # Awards
            if candidate_data.get('awards'):
                doc.add_paragraph('AWARDS', style='Heading 2')
                for award in candidate_data.get('awards', []):
                    doc.add_paragraph(award, style='List Bullet')
                doc.add_paragraph()
            
            # Technical Skills
            if candidate_data.get('technical_skills'):
                doc.add_paragraph('TECHNICAL SKILLS', style='Heading 2')
                tech_para = doc.add_paragraph(', '.join(candidate_data.get('technical_skills', [])))
                tech_para.paragraph_format.space_after = Pt(12)
            
            # Save document
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path)
            logging.info(f'Word document saved to {output_path}')
            return output_path
            
        except Exception as e:
            logging.error(f'Error building Word document: {e}')
            raise

if __name__ == '__main__':
    setup_logging()
    resume_builder = ResumeBuilder()
