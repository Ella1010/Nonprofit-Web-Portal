
# PEAR Application Portal

The PEAR Application Portal is a full-stack web application built to support the Program for Excellence in African Research (PEAR),
a hands-on STEM summer program for high school students in Africa.
The portal enables secure application submission, document uploads, dynamic activity entries, autosave functionality, and a dedicated admin dashboard for reviewing applicant data.

## Features

### Applicant-Facing

* Multi-step application form with autosave across all sections.
* Dynamic activity blocks with add/remove support.
* File uploads for grade reports and supplemental documents.
* Email verification with a six-digit code and duplicate-application prevention.
* Review page summarizing all entered information prior to submission.
* Post-submission read-only dashboard for applicants.
* Mobile-responsive UI with a modern design.

### Admin-Facing

* Secure admin login portal.
* Dashboard to view, search, and filter applications.
* Applicant detail pages with downloadable PDF summaries.
* CSV export for selected or all applications.
* Access to uploaded grade reports and supporting files.
* Application status and timestamp tracking.

## Technology Stack

### Backend

* Python
* Flask
* PostgreSQL
* SQLAlchemy
* Flask-Mail
* Jinja2 templating

### Frontend

* HTML, CSS, JavaScript
* Responsive layout components
* Clean, accessible form design

### Infrastructure

* Hosted on Render
* Persistent Disk usage for file storage
* Environment-based configuration for secure deployment

## Folder Structure (Simplified)

```
project/
│
├── app.py
├── config.py
├── requirements.txt
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/
├── db/
│   ├── init.sql
│   └── models.py
└── README.md
```

## Purpose

This portal was built to streamline PEAR's application process, improve data integrity, and provide an organized platform for both applicants and program administrators. 
It supports the program’s mission of expanding access to high-quality STEM education and research opportunities for students in Africa.

