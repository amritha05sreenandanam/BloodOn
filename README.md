# Blood Donation Alert System

A comprehensive web platform that connects voluntary blood donors with hospitals and patients in urgent need of blood donations. The system automatically matches blood requests with compatible donors based on blood type and location, sending timely notifications via email and WhatsApp.

## 🎯 Project Overview

The Blood Donation Alert System is a social service–driven web platform designed to bridge the gap between urgent medical needs and compassionate individuals willing to help. It enables:

- **Donors** to register and join a network of life-savers
- **Hospitals** to submit urgent blood requests quickly
- **Automatic matching** based on blood compatibility and location
- **Instant notifications** via email and WhatsApp
- **Real-time statistics** of registered donors

## 🏗️ Architecture

### Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python 3.x, Flask
- **Database**: MySQL
- **Notifications**: SMTP (Email), Twilio API (WhatsApp)
- **Development**: Flask-CORS for API handling

### Project Structure

```
blood-donation-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── templates/            # HTML templates
│   ├── index.html        # First page (Login/Entry)
│   ├── donor_form.html   # Donor registration form
│   ├── requester_form.html # Hospital request form
│   ├── main.html         # Main statistics page
│   ├── details.html      # Information & FAQ page
│   └── donor_match.html  # Donor match results page
└── static/              # Static assets
    ├── css/
    │   └── style.css     # Main stylesheet
    └── js/
        ├── donor_form.js      # Donor form handler
        ├── requester_form.js  # Requester form handler
        └── details.js         # FAQ accordion
```

## 📋 Features

### For Donors
- Simple registration form
- Automatic matching with blood requests
- Email and WhatsApp notifications
- Privacy protection (no public display of personal info)

### For Hospitals/Requesters
- Quick blood request submission
- Automatic donor matching
- Real-time match statistics
- Direct donor contact information

### System Features
- Blood compatibility matrix
- Location-based matching
- Real-time donor statistics
- Impact tracking (connections made)
- Comprehensive FAQ section
- Mobile-responsive design

## 🚀 Setup Instructions

### Prerequisites

1. **Python 3.7+** installed
2. **MySQL Server** installed and running
3. **pip** (Python package manager)
4. **Git** (optional, for cloning)

### Step 1: Database Setup

1. Create a MySQL database:
```sql
CREATE DATABASE blood_donation_db;
```

2. Note your MySQL credentials (host, username, password, port)

### Step 2: Install Dependencies

1. Navigate to the project directory:
```bash
cd "C:\Users\user\OneDrive\Desktop\hello cursor"
```

2. Install Python packages:
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` file with your actual credentials:

```env
# Database Configuration
DB_HOST=localhost
DB_NAME=blood_donation_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_PORT=3306

# Email Configuration (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# WhatsApp Configuration (Twilio)
WHATSAPP_ACCOUNT_SID=your_twilio_account_sid
WHATSAPP_AUTH_TOKEN=your_twilio_auth_token
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886
```

**Important Notes:**
- For Gmail: Use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password
- For WhatsApp: Sign up for [Twilio](https://www.twilio.com/) and get your credentials
- WhatsApp integration is optional - the system will work without it

### Step 4: Run the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. The database tables will be created automatically on first run.

## 📱 Usage Guide

### For Donors

1. Click **"Donor Login"** on the home page
2. Fill in the registration form:
   - Full Name
   - Blood Group (select from dropdown)
   - Email Address
   - Phone Number (with country code)
   - Location (City, District)
3. Click **"Confirm Registration"**
4. You'll be redirected to the main page
5. You'll receive alerts via email and WhatsApp when there's a matching request

### For Hospitals/Requesters

1. Click **"Requester Login"** on the home page
2. Fill in the request form:
   - Hospital Information (name, email, phone, location)
   - Required Blood Group
   - Optional: Patient Details
   - Urgency Level
3. Click **"Submit Request"**
4. View the donor match page showing:
   - Number of nearby compatible donors notified
   - Number of compatible donors in other locations
5. Donors will contact you directly using the provided information

## 🎨 Design Philosophy

The system follows a **clean, calm, and trustworthy** design approach:

- **Minimalist UI** to reduce cognitive load during emergencies
- **Emotionally reassuring** rather than alarming
- **Fast and accessible** for critical moments
- **Mobile-responsive** for use on any device
- **Privacy-focused** with no public exposure of personal data

## 🔒 Security & Privacy

- Donor personal information is never displayed publicly
- Only hospitals receive contact details when matched
- Data is securely stored in MySQL database
- Environment variables for sensitive credentials
- Input validation on both client and server side

## 🧪 Testing

### Manual Testing Checklist

1. **Donor Registration**
   - [ ] Register a new donor
   - [ ] Verify redirect to main page
   - [ ] Check donor count increases
   - [ ] Verify blood group and location statistics update

2. **Blood Request**
   - [ ] Submit a blood request
   - [ ] Verify donor matching works
   - [ ] Check email notifications (if configured)
   - [ ] Verify redirect to match page

3. **Statistics**
   - [ ] View main page statistics
   - [ ] Verify blood group counts
   - [ ] Verify location-wise counts

4. **Navigation**
   - [ ] Test all page links
   - [ ] Verify FAQ accordion works
   - [ ] Check mobile responsiveness

## 🐛 Troubleshooting

### Database Connection Issues

- Verify MySQL server is running
- Check database credentials in `.env`
- Ensure database exists: `CREATE DATABASE blood_donation_db;`

### Email Not Sending

- Verify SMTP credentials in `.env`
- For Gmail: Use App Password, not regular password
- Check firewall/network settings
- Verify SMTP server and port are correct

### WhatsApp Not Working

- WhatsApp integration requires Twilio account
- System will continue working without WhatsApp
- Check Twilio credentials in `.env`
- Verify phone number format includes country code

### Port Already in Use

- Change port in `app.py`: `app.run(port=5001)`
- Or stop the process using port 5000

## 📊 Database Schema

### Tables

1. **donors**
   - id (Primary Key)
   - name, blood_group, email, phone, location
   - created_at

2. **blood_requests**
   - id (Primary Key)
   - hospital_name, hospital_email, hospital_phone, hospital_location
   - required_blood_group, patient_details, urgency_level
   - status, created_at

3. **matches**
   - id (Primary Key)
   - request_id (Foreign Key)
   - donor_id (Foreign Key)
   - notified_at

## 🔮 Future Enhancements

- Donor profile update functionality
- Advanced location matching with GPS/geocoding
- SMS notifications as alternative
- Admin dashboard
- Donation history tracking
- Donor availability calendar
- Multi-language support

## 📝 License

This project is created for social service purposes. Feel free to use and modify as needed.

## 🤝 Contributing

This is a standalone project, but suggestions and improvements are welcome!

## 📞 Support

For issues or questions:
1. Check the FAQ section on the Details page
2. Review this README
3. Check database and environment configurations

## 🙏 Acknowledgments

Built with compassion for those in need. Thank you to all blood donors who make this system meaningful.

---

**Remember**: This system is a tool to connect people. The real heroes are the donors who selflessly help others in times of need. 🩸❤️

