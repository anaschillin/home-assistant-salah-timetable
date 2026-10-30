# Security reporting

Use GitHub's **Security → Report a vulnerability** when private reporting is
available for this repository. If it is unavailable, open an issue requesting a
private contact method without including exploit details, credentials, private URLs
or imported timetable content. No separate security contact address is advertised.

Include the affected integration/Home Assistant versions, installation method,
reproduction steps using synthetic input, impact and any proposed fix. Maintainers
will assess reports on a best-effort basis; no response-time guarantee is offered.

The current candidate is the maintained development version. Older snapshots do
not have a separate long-term security maintenance commitment. See
[compatibility and support](docs/getting-started.md#support-and-compatibility-policy) for the tested platforms and source
limitations.

## Dependency advisories

The integration declares pypdf as its additional runtime dependency. Development
and compatibility locks also include Home Assistant and its exact transitive
requirements. Review the repository's [dependency alerts](https://github.com/anaschillin/home-assistant-salah-timetable/security/dependabot)
alongside candidate test results: passing compatibility tests does not resolve
an upstream security advisory. Keep CI's package installer patched independently
of the versions required inside each Home Assistant environment.

When an upstream Home Assistant pin prevents an advisory fix, record the affected
package, supported versions and remediation constraint in the release review.
Do not dismiss the alert or override Home Assistant's requirements solely to make
the report green; a supported upstream update or a reviewed support-policy change
is required.
