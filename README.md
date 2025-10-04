# Online-Voting
The Online Voting System is a secure and user-friendly web application that enables digital elections. It allows administrators to create and manage elections, add candidates, and monitor live results, while voters can securely cast their votes online.

This project is designed as a group project to demonstrate concepts of web development, database management, and data visualization.

**👥 Group Members
1. Aditya Raj
2. Ranjan Kumar
3. Anushka Singh
4. Amritanshu Kumar**

**🧰 Technologies Used**
**Category	              Technologies**
Frontend	            HTML5, CSS3, Bootstrap
Backend	              Python (Flask Framework)
Database	            SQLite3
Visualization  	      Chart.js (Pie and Line Charts)
Security	            Session management, CAPTCHA authentication
Version Control	      Git & GitHub

**⚙️ Features**

**👨‍💻 User Side**

. User Registration & Login (with CAPTCHA verification)
. Secure session-based authentication
. Dynamic election selection
. Real-time voting system (one vote per election)

**🧑‍💼 Admin Side**

. Admin login with session control

. Create and manage elections

. Add and remove candidates

. Monitor live vote counts

. View election statistics and winner results

**🗂️ Database Schema**

**Tables:**

**1. users**

  . id – Primary Key
  . username – Unique Username
  . password – Encrypted Password

**2. elections**

  . id – Primary Key
  . name – Election Name
  . start_time – Election Start Date/Time
  . end_time – Election End Date/Time

**3. candidates**

  . id – Primary Key
  . name – Candidate Name
  . election – Linked Election Name
  . votes – Vote Count

**🚀 Working Procedure**

**1️⃣ Setup**

  . Install Python (3.8 or above)
  . Clone this repository
  
