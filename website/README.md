# Develoop public site

This directory contains the public Develoop product, support, privacy, terms,
and release pages deployed with Sites.

## Local development

Requires Node.js 22.13 or later.

```bash
npm install
npm run dev
npm test
```

The site is informational and public. It does not use authentication, forms,
analytics, D1, R2, or runtime secrets.

## Routes

- `/`: product overview and installation paths
- `/support`: support and safe issue-reporting guidance
- `/privacy`: plugin and website privacy policy
- `/terms`: terms and mixed-license boundary
- `/releases`: public release notes

Run `npm test` after source changes. The test script builds the production
Worker and renders every public route.
