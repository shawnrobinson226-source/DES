# DES Local Launch Specification

## Scope

This is the supported local-development launch for the DES FastAPI service.
It is deliberately bound to IPv4 loopback and is not a public deployment
specification. DES endpoints do not authenticate callers, so changing the bind
address requires a separate security design and review.

## Runtime

Use Python 3.11 and install the exact runtime dependencies from the repository
root:

```powershell
python -m pip install -r requirements.txt
```

`requirements.txt` pins the FastAPI version used by the verified environment
and the ASGI server used by the launcher. Development and test dependencies are
not described by this runtime file.

## Operator Question-Set Activation

Activation is explicit and versioned. With the variable absent or empty, the
operator registry remains empty and an operator start fails closed with
`QUESTION_SET_UNAVAILABLE`.

The only accepted production selection in this version is:

```powershell
$env:DES_OPERATOR_QUESTION_SET = "tri_operator_classification@1.0.0"
```

Whitespace, aliases, `latest`, and unknown ids or versions stop application
startup. There is no fallback. The selected set is registered and activated
before the FastAPI application is constructed.

## Launch

Optionally choose an unprivileged port; the default is 8000:

```powershell
$env:DES_PORT = "8000"
python ui/run_des.py
```

The launcher fixes the host to `127.0.0.1`. There is no environment variable or
command-line option for `0.0.0.0`, a LAN address, or IPv6. The port must contain
ASCII digits and be from 1024 through 65535.

Check the local health endpoint from the same machine:

```text
http://127.0.0.1:8000/health
```

## AXIS Boundary

The operator interaction routes make no AXIS request. Do not configure AXIS
credentials merely to launch or exercise DES questions. The first live AXIS
request remains a separate, explicitly approved trial step at the Sapphire
plugin boundary.

## Security Boundary

- Loopback binding is a compensating control, not endpoint authentication.
- The automated launch proof starts the checked-in launcher on a random
  loopback port, reads `/health`, and begins one operator interaction.
- The proof establishes the launcher bind and application behavior on the test
  host. It does not establish firewall policy, container networking, reverse
  proxy policy, or suitability for remote deployment.
- No access token, service key, operator id, or AXIS credential belongs in this
  repository or in the launch command.
