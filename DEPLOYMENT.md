# Deployment Guide for Render.com

## Environment Variables Setup

This application requires the following environment variables to be configured in your Render service:

### Required Environment Variables:

| Variable Name | Description | Example Value |
|---------------|-------------|---------------|
| `USE_AUTH` | Enable/disable authentication | `false` |
| `FHIR_SERVER` | FHIR server endpoint URL | `https://smile.sparked-fhir.com/ereq/fhir/DEFAULT` |
| `FHIR_USERNAME` | FHIR server username | `placer` |
| `FHIR_PASSWORD` | FHIR server password | `your_password_here` |

### Setting up Environment Variables in Render:

1. Go to your Render service dashboard
2. Click on the "Environment" tab
3. Add each environment variable using the "Add Environment Variable" button
4. Use the exact variable names listed above
5. Enter your actual values (never commit these to the repository)

### For Local Development:

1. Copy `.env.example` to `.env`
2. Fill in your actual credentials in the `.env` file
3. The `.env` file is already ignored by git and won't be committed

### Security Notes:

- **NEVER** commit actual credentials to the repository
- Use Render's environment variable feature for production deployment
- Keep your `.env` file local only
- The `.env.example` file shows the required structure without exposing credentials
