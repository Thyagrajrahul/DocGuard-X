
# DocGuard-X

## Explainable AI-Based Insider Threat Detection in Electronic Health Record Systems

### Project Overview

DocGuard-X is a simulated healthcare security monitoring application designed to demonstrate access control, activity logging, and AI-based anomaly detection in healthcare data exchange.

The application provides separate Administrator and Doctor roles.

### Main Features

- Administrator and Doctor authentication
- Role-based access control
- Doctor-patient assignment management
- Patient record access restrictions
- Assignment activation and deactivation
- Authorized and denied activity logging
- Security event monitoring
- AI-based healthcare traffic classification
- Batch dataset analysis
- Human-readable explanations for detected indicators
- Model evaluation using precision, recall, F1-score and false-positive rate

### Technology Stack

- Python
- Flask
- SQLite
- SQLAlchemy
- HTML, CSS and JavaScript
- Bootstrap
- Scikit-learn
- Pandas and NumPy
- Joblib
- Pytest

### Project Structure

```text
DocGuard-X/
├── app/
│   ├── activity/
│   ├── admin/
│   ├── auth/
│   ├── authorization/
│   ├── database/
│   ├── doctor/
│   ├── explanations/
│   ├── ml/
│   ├── static/
│   └── templates/
├── data/
├── dataset/
├── docs/
├── reports/
├── tests/
├── instance/
├── create_admin.py
├── requirements.txt
└── README.md
```

### Installation

1. Install Python 3.12 or a compatible version.
2. Open PowerShell in the project directory.
3. Create a virtual environment:

```powershell
python -m venv venv
```

4. Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

5. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Running the Application

Start the Flask application:

```powershell
python -c "from app import create_app; app = create_app(); app.run(debug=True)"
```

Open:

http://127.0.0.1:5000

### Administrator Setup

Create an administrator account:

```powershell
python create_admin.py
```

Follow the prompts to create the account.

### Testing

Run the complete automated test suite:

```powershell
python -m pytest -q
```

### AI Model

The project uses a trained HistGradientBoosting classification model to identify potentially anomalous healthcare data-exchange traffic.

The model uses traffic characteristics and excludes ground-truth labels from prediction features.

The application supports two threshold strategies:

- Best F1
- Lower false-positive rate

### Security Scope

This is an academic simulation using synthetic healthcare data.

It is not a production hospital information system and must not be used to process real patient records.

AI alerts indicate potentially unusual activity and do not establish malicious intent.

### Limitations

- Dataset-based traffic detection is not direct proof of doctor insider activity.
- Model performance depends on the dataset and its distribution.
- Rule-based explanations are indicators, not formal causal explanations.
- Further validation is required before any real-world deployment.

### Dataset Attribution

Include the original dataset name, source and CC BY 4.0 attribution in the final project report and presentation.

### Project Status

Academic prototype with authentication, authorization, activity logging, AI traffic monitoring and automated tests.
