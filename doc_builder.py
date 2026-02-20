from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement


def build_resume(name, sections):
    \"\"\"Creates a resume document with the specified name and sections.\"\"\"  
    document = Document()
    
    # Add name
    name_paragraph = document.add_paragraph()  
    name_run = name_paragraph.add_run(name)
    name_run.bold = True
    name_run.font.size = Pt(22)  
    name_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    name_paragraph.add_run().add_break()  

    # Add sections
    for section_title, section_content in sections.items():
        # Add section title
        title_paragraph = document.add_paragraph()  
        title_run = title_paragraph.add_run(section_title)
        title_run.bold = True
        title_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        
        # Add border to section title
        border = OxmlElement('w:pBdr')
        border_el = title_paragraph._element.add_element(border)
        title_paragraph._element.append(border_el)

        # Add section content
        content_paragraph = document.add_paragraph(section_content, style='ListBullet')
        content_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT 
        
    # Set body text font style
    for paragraph in document.paragraphs:
        if paragraph != name_paragraph:
            for run in paragraph.runs:
                run.font.name = 'Calibri'
                run.font.size = Pt(11)
    
    # Save the resume
    document.save('resume.docx')
