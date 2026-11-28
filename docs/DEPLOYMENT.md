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
limits and buffers upload bodies to 192 KiB; responses are not spilled to disk.
HTML and CSS are compressed in transit when the browser accepts gzip.
Gunicorn and converter proxy delivery limits are 180 seconds: a large Manual
document can keep a response open while the browser parses it. The former
30-second worker limit could truncate a native reset response. Converter
liveness allows eight failed 30-second checks so two busy sync workers can
finish within that delivery limit; readiness continues to gate new traffic.
The converter has a separate 352 MiB memory-backed `/tmp` and a read-only root
filesystem. Temporary generated files are removed before returning the response;
no ROM/artifact volume or database is used. Both containers must be ready for a
pod to receive traffic. Changing either image requires a fresh shared tag.

A worst-case dense 128 KiB MBC1 checkpoint document is bounded below 160 MiB.
The converter requests 256 MiB and allows 3,072 MiB for two workers plus tmpfs.
The 352 MiB temporary volume accommodates two simultaneous generated pages.
Two concurrent 128 KiB dense Manual conversions were verified under that limit:
responses below 159 MiB, temporary files below 316 MiB, and less than 2.1 GiB peak total
container memory with no OOM events. Files remain request-local and are removed
before returning the response.

Bump Chart.yaml version/appVersion and values.yaml image.tag together before
building changed image inputs. Never reuse tags with IfNotPresent. Merge the app
PR, build/deploy the merged main commit, then record that deployed commit as
`games/dmgss` in selfhosted. Use selfhosted's sync-submodules script for later pin
updates; never develop inside its submodule checkout.

No application secrets are required. `values.local.tpl.yaml` is intentionally
empty and no resolved values.local.yaml is created. The example file records
this provenance. Registry authentication is provided by the existing build
session, and ingress delegates authentication to the existing Authelia service.
