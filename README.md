# Resume Generator

## Setup Instructions

1. Install the necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

## Example Request Bodies

### Endpoint 1: /generate_resume
```json
{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "experience": [
        {
            "job_title": "Software Engineer",
            "company": "ABC Corp",
            "years": 3
        }
    ]
}
```

### Endpoint 2: /fetch_resume
```json
{
    "resume_id": "12345"
}
```

### Endpoint 3: /delete_resume
```json
{
    "resume_id": "12345"
}
```

## Testing Instructions

You can test the API using the following link:

[API Docs](http://127.0.0.1:8000/docs)  
