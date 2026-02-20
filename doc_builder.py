from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

class ResumeBuilder:
    def __init__(self):
        self.document = Document()

    def add_name(self, name):
        name_paragraph = self.document.add_paragraph() 
        name_run = name_paragraph.add_run(name)
        name_run.bold = True
        name_run.font.size = Pt(22)
        name_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        name_paragraph.add_run().add_break()  # Add some space after the name

    def add_section(self, heading):
        section_paragraph = self.document.add_paragraph()
        section_run = section_paragraph.add_run(heading)
        section_run.bold = True
        section_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        section_paragraph.add_run().add_break()  # Add some space after the heading
        section_paragraph.add_run('------').bold = True  # Add a bottom border effect

    def add_body_text(self, text):
        body_paragraph = self.document.add_paragraph(text)
        body_paragraph.style.font.size = Pt(11)
        body_paragraph.style.font.name = 'Calibri'

    def add_bullet_points(self, points):
        for point in points:
            bullet_paragraph = self.document.add_paragraph(point, style='ListBullet')
            bullet_paragraph.style.font.size = Pt(11)
            bullet_paragraph.style.font.name = 'Calibri'

    def save(self, filename):
        self.document.save(filename)

# Example Usage
if __name__ == '__main__':
    resume_builder = ResumeBuilder()
    resume_builder.add_name('John Doe')
    resume_builder.add_section('Experience')
    resume_builder.add_body_text('Software Engineer at Company XYZ')
    resume_builder.add_bullet_points(['Developed applications', 'Led a team', 'Achieved targets'])
    resume_builder.save('resume.docx')
