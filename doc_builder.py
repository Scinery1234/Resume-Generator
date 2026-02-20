import logging

# Set up logging
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ResumeBuilder:
    def __init__(self):
        self.resume_data = {}

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

    def build_resume(self):
        try:
            # Code to format resume_data into a resume structure
            resume = f"{self.resume_data['name']}\n{self.resume_data['contact_info']}\n"  
            resume += 'Experience:\n'
            for exp in self.resume_data['experience']:
                resume += f"- {exp}\n"
            resume += 'Education:\n'
            for edu in self.resume_data['education']:
                resume += f"- {edu}\n"
            logging.info('Resume built successfully')
            return resume
        except Exception as e:
            logging.error(f'Error building resume: {e}')
            return 'Error building resume'

if __name__ == '__main__':
    setup_logging()
    resume_builder = ResumeBuilder()
    # Here you would typically collect data from the user
