# 📊 CyberArk Business Intelligence with Amazon QuickSight 🔒

Welcome to Project CABI, the CyberArk Business Intelligence with Amazon QuickSight project repository! This community-developed project leverages AWS services and advanced BI visualization to automate monitoring and analysis of CyberArk Privileged Access Management (PAM) metrics.  

Whether you're managing on-premises or cloud-based PAM environments, this project demonstrates the use of modern cloud technologies to address key business needs around compliance, access control, and security analytics.  

![Account Compliance BI Visualization](/assets/accountComplianceVisualization.png)

## 📋 Project Overview

Project CABI is an automated and scalable Proof of Concept (PoC) designed to provide real-time visibility into PAM data. It automates the ingestion of PAM data from CyberArk APIs and logs, normalizes and stores it in a managed AWS RDS database, and delivers customizable KPIs and reports through Amazon QuickSight dashboards. This solution was built to solve critical pain points faced by organizations managing large-scale CyberArk deployments, such as:

## 💵 Business Use Cases

- **Compliance Reporting**
   - Ensure adherence to internal security policies and external regulations (e.g., SOX, GDPR, PCI DSS) by automating password age, policy enforcement, and access audit checks.
   - Example KPI: Accounts with overdue password changes.
- **Security Incident Monitoring**
   - Identify and respond to security anomalies by monitoring events such as failed logins, unauthorized access attempts, and privileged session activity.
   - Example KPI: Time to detect and respond to critical events.
- **Operational Efficiency**
   - Improve time-to-resolution for operational issues by centralizing performance data, platform health metrics, and password rotation efficiency.
   - Example KPI: Auto-reconciliation success rates for PAM-managed platforms.
- **Capacity Planning**
   - Enable IT and Security teams to monitor user and account growth trends across platforms and regions, supporting resource allocation and future infrastructure planning.
   - Example KPI: Growth of managed accounts per platform over time.

## 🤩 Features

- **Data Ingestion**: Extract CyberArk PAM data (Safes, Accounts, Platforms) via APIs or logs.
- **Data Processing**: Transform data using AWS Lambda functions.
- **Data Visualization**: Generate interactive dashboards in AWS QuickSight.
- **Secure Architecture**: Leverages AWS Secrets Manager, IAM roles, and VPC for security.
- **Automation**: Scheduled workflows and alerts for continuous monitoring.

## 🛠️ Technologies Used
   
- **CyberArk PAM**: Self-Hosted and Privilege Cloud solutions.
- **CyberArk Secrets Manager**: Central Credential Provider (CCP) for secure credential handling.
- **AWS Services**: Lambda, S3, RDS (PostgreSQL), Secrets Manager, CloudWatch, EventBridge, QuickSight.
- **Languages**: PowerShell, Python, JSON.
- **Tools**: Visual Studio Code, AWS CLI, PostgreSQL client (psql).

## 📚 Documentation & Guide

For a complete guide on setting up and configuring the project, please refer to the detailed Project Guide PDF. This document walks you through:

- Setting up all necessary AWS services.
- Configuring CyberArk APIs for data extraction.
- Deploying Lambda functions for data ingestion and transformation.
- Creating and customizing QuickSight dashboards.

## 📐 Architecture

### **Services Architecture**

![Services Architecture Diagram](/diagrams/CyberArkDashboardArchitecture.png)

### **Sequence Diagram**

![Sequence Diagram](/diagrams/CyberArkQuickSightSequenceDiagram.png)

## 🤝 Contributing

Some ideas for collaboration:

- **Front End Development**: React or Vue.js frontend to eliminate dependence on QuickSight.
- **Expanded Ingest Methods**:
   - EventBridge API integration
   - Vault logs (italog, trace.d*).
   - Vault configurations (dbparm, LDAPConf).
   - Server performance details (CPU, Memory, Network).
   - Component logs (CPM, PSM, PSM for SSH).
   - Component configurations.
   - PVWA System Health.
   - Certificate management.
- **Expanded ETL Options**:
   - Support for AWS Glue and/or Athena for large datasets.
- **CI/CD Automation**:
   - GitHub Actions workflows.
- **Infrastructure as Code**:
   - CloudFormation template for easy setup.

## 🔗 Connect with the Author

Hi, I'm Eli Hopkins! You can find me on [GitHub](https://github.com/IAM-Jah), [LinkedIn](https://www.linkedin.com/in/ewhopkins/) and my [blog](https://elihopkins.com/). Feel free to reach out with any questions, suggestions or ideas for collaboration!

## 📄 License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Disclaimer

This repository is for informational purposes and does not constitute legal advice. Ensure to consult with compliance and legal professionals for specific guidance. This is an unofficial repository and is not affiliated with CyberArk Software, Ltd.  
