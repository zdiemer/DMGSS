# Homelab deployment

URL: https://dmgss.zachd.duckdns.org — existing Authelia login required.
The source repository is public. Authenticated ingress keeps the running
experimental build within the existing homelab access model. No Cloudflare public host is configured.

From the standalone `/home/node/code/DMGSS` checkout:

```sh
./build.sh
./upgrade.sh
```

The image is built in Docker or the workspace's shared BuildKit and pushed to
`registry.zachd.duckdns.org/zdiemer/dmgss`. The `games/dmgss` Helm release serves
static files through two unprivileged nginx replicas, with readiness/liveness
checks, a disruption budget, node spreading and graceful drain. Each pod also
runs the `dmgss-converter` image at the same version: two Gunicorn workers handle
`/convert/` behind nginx and the existing Authelia ingress. The converter port
is not exposed by the Service. No new public route bypasses authentication.

`./build.sh` builds/pushes both Docker targets (`web` and `converter`). nginx
limits and buffers upload bodies to 64 KiB; responses are not spilled to disk.
The converter has a separate 32 MiB memory-backed `/tmp` and a read-only root
filesystem. Temporary generated files are removed before returning the response;
no ROM/artifact volume or database is used. Both containers must be ready for a
pod to receive traffic. Changing either image requires a fresh shared tag.

Dense conversion can produce an 8 MiB checkpoint document. A local worst-case
run peaked around 131 MiB RSS, so the converter requests 128 MiB and allows
512 MiB for its two workers and temporary files. The 32 MiB temporary volume
allows two full-size conversions concurrently; generated files are still
request-local and removed before the response returns.

Bump Chart.yaml version/appVersion and values.yaml image.tag together before
building changed image inputs. Never reuse tags with IfNotPresent. Merge the app
PR, build/deploy the merged main commit, then record that deployed commit as
`games/dmgss` in selfhosted. Use selfhosted's sync-submodules script for later pin
updates; never develop inside its submodule checkout.

No application secrets are required. `values.local.tpl.yaml` is intentionally
empty and no resolved values.local.yaml is created. The example file records
this provenance. Registry authentication is provided by the existing build
session, and ingress delegates authentication to the existing Authelia service.
