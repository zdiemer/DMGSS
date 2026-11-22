# Homelab deployment

URL: https://dmgss.zachd.duckdns.org — existing Authelia login required.
The private repository and authenticated ingress keep this experimental build
within the existing homelab access model. No Cloudflare public host is configured.

From the standalone `/home/node/code/DMGSS` checkout:

```sh
./build.sh
./upgrade.sh
```

The image is built in Docker or the workspace's shared BuildKit and pushed to
`registry.zachd.duckdns.org/zdiemer/dmgss`. The `games/dmgss` Helm release serves
static files through two unprivileged nginx replicas, with readiness/liveness
checks, a disruption budget, node spreading and graceful drain.

Bump Chart.yaml version/appVersion and values.yaml image.tag together before
building changed image inputs. Never reuse tags with IfNotPresent. Merge the app
PR, build/deploy the merged main commit, then record that deployed commit as
`games/dmgss` in selfhosted. Use selfhosted's sync-submodules script for later pin
updates; never develop inside its submodule checkout.

No application secrets are required. `values.local.tpl.yaml` is intentionally
empty and no resolved values.local.yaml is created. The example file records
this provenance. Registry authentication is provided by the existing build
session, and ingress delegates authentication to the existing Authelia service.
