kubectl create -f pipelinerun.yaml

voyage/
├── Dockerfile
├── app.py
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── ingress.yaml
│   ├── namespace.yaml
│   └── service.yaml
├── tekton/
│   ├── README.md                    # core pipeline setup
│   ├── 02-pipeline.yaml             # the 5-stage Pipeline definition
│   ├── 03-pipelinerun.yaml          # manual trigger (fsGroup + secret key fix applied)
│   ├── pipeline.yaml                # ← the file you've been running kubectl apply/create against
│   ├── tasks/
│   │   ├── python-test.yaml         # Stage 2: install deps + run tests
│   │   ├── trivy-scanner.yaml       # Stage 4: vulnerability scan (exit-code 0, report-only)
│   │   └── update-manifest.yaml     # Stage 5: bump tag, commit (safe.directory fix applied)
│   └── triggers/                    # ← new: automatic webhook-based triggering
│       ├── README.md                # setup steps + home-lab NAT caveat
│       ├── 00-rbac.yaml             # ServiceAccount + Role/RoleBinding for the EventListener
│       ├── 01-triggerbinding.yaml   # extracts repo-url/revision from GitHub payload
│       ├── 02-triggertemplate.yaml  # defines the PipelineRun to auto-create
│       └── 03-eventlistener.yaml    # receives the GitHub webhook POST
├── requirements.txt
└── ...


GitHub
   │
   │ HTTPS webhook
   ▼
ngrok public URL
   │
   │ tunnel
   ▼
your homelab machine
   │
   │ NodePort
   ▼
Tekton EventListener
   │
   ▼
TriggerBinding
   │
   ▼
TriggerTemplate
   │
   ▼
PipelineRun
