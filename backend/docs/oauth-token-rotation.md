# OAuth Token Rotation Procedure

## Overview

Rebug stores OAuth tokens (Jira, Slack) encrypted using Fernet symmetric encryption. This document describes the procedure for rotating the encryption key without losing access to existing tokens.

## Current Implementation

Tokens are encrypted with `TOKEN_ENCRYPTION_SECRET` before storage in the `integrations` table:

```python
from cryptography.fernet import Fernet

fernet = Fernet(settings.token_encryption_secret.encode())
encrypted_token = fernet.encrypt(token.encode())
```

## Key Rotation Strategy

### Option 1: Zero-Downtime Rotation (Recommended)

Implement key versioning to support multiple keys during rotation.

### Rotation Steps

1. **Add new key as primary, keep old as secondary**
2. **Update encryption service to use both keys**
3. **Run migration to re-encrypt all tokens**
4. **Verify all tokens are re-encrypted**
5. **Remove old key from configuration**

## Generating a New Key

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
```

## Emergency Recovery

If rotation fails:

1. Keep the old key available in `TOKEN_ENCRYPTION_SECRET_OLD`
2. Tokens encrypted with the old key will still be decryptable
3. Re-run the migration script after fixing issues

## Best Practices

1. **Rotate keys every 90 days** (or per your security policy)
2. **Test rotation in staging first**
3. **Keep keys in a secrets manager** (Doppler, AWS Secrets Manager, etc.)
4. **Never commit keys to version control**
5. **Audit key access** - who can view/rotate keys

## Monitoring

Add alerts for:
- Failed decryption attempts
- Key rotation failures
- Tokens approaching expiration
