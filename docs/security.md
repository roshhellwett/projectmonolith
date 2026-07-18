# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Project Monolith, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. Email the maintainer directly at the contact listed on the [Zenith Open Source Projects](https://zenithopensourceprojects.vercel.app/) website.
3. Include a clear description of the vulnerability, steps to reproduce, and potential impact.

### What to Expect
- **Acknowledgment**: Within 48 hours of your report.
- **Resolution**: We aim to patch confirmed vulnerabilities within 7 days.
- **Credit**: Reporters will be credited in the changelog unless they prefer to remain anonymous.

## Security Best Practices

### For Users
- Never share your activation key with anyone.
- Keep your Telegram account secure with 2FA.
- Be cautious of phishing attempts impersonating Zenith bots.

### For Developers
- Never commit `.env` files or API tokens to the repository.
- Always set a strong, random `WEBHOOK_SECRET` in production.
- Keep all dependencies updated to their latest patch versions.
- Run `python security_check.py` before deploying.

## Security Features Implemented

### Webhook Authentication
All bot webhooks require secret token validation:
- `/webhook/admin/{secret}`
- `/webhook/group/{secret}`
- `/webhook/ai/{secret}`
- `/webhook/crypto/{secret}`
- `/webhook/support/{secret}`

### Rate Limiting
- Per-IP rate limiting on all endpoints
- Admin commands have additional rate limiting (10-60 seconds between calls)
- AI query limits per user tier (5/hour free, 60/hour pro)

### Input Sanitization
- Prompt injection protection for AI commands
- SQL injection prevention via parameterized queries
- XSS prevention via HTML escaping

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: geolocation=(), microphone=(), camera=()

### Database Security
- SSL/TLS enforced for all database connections
- Connection timeouts configured (10s connect, 30s command)
- Connection pooling with overflow limits

## Running Security Checks

```bash
# Install safety for vulnerability scanning
pip install safety

# Run security check
python security_check.py
```

## Dependency Management

Regularly update dependencies to patch security vulnerabilities:

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Update all packages
pip install -r requirements.txt --upgrade
```

## Incident Response

In case of a security breach:

1. **Contain**: Immediately rotate all exposed credentials
2. **Assess**: Determine scope of the breach
3. **Notify**: Alert affected users within 24 hours
4. **Remediate**: Fix vulnerabilities and patch systems
5. **Review**: Document lessons learned and improve defenses
