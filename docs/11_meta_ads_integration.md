# Meta Ads API Integration Plan

> Connect ad accounts to get real performance data for data-driven creative strategy.

---

## Why This Matters

Parker charges $299-699/mo partly because they can connect to Meta Ad accounts and show:
- Which ads are actually performing (not just guessing from Ad Library)
- Real CPM, CPC, ROAS, CTR metrics
- Performance trends over time
- Which hooks/angles convert best

This turns the scraper from "research tool" into "performance optimization tool".

---

## Technical Requirements

### 1. Meta App Setup

```
1. Create Meta App at developers.facebook.com
2. Add "Marketing API" product
3. Configure OAuth redirect URIs
4. Request required permissions:
   - ads_read (required for Insights API)
   - ads_management (optional, for future features)
   - business_management (for agency multi-account)
```

### 2. Permissions Needed

| Permission | Purpose | Review Required |
|------------|---------|-----------------|
| `ads_read` | Read ad performance data | Yes |
| `read_insights` | Access account insights | Yes |
| `ads_management` | Modify campaigns (future) | Yes |

### 3. OAuth Flow

```
User clicks "Connect Meta Ads"
  → Redirect to Facebook OAuth
  → User grants permissions
  → Receive access_token
  → Exchange for long-lived token (60 days)
  → Store encrypted in database
  → Refresh before expiry
```

---

## API Endpoints

### Get Ad Account Insights

```
GET /act_{ad_account_id}/insights

Fields:
- impressions
- reach  
- clicks
- spend
- cpc (cost per click)
- cpm (cost per 1000 impressions)
- ctr (click through rate)
- frequency
- actions (conversions)
- action_values (conversion values)
- purchase_roas
```

### Get Ad-Level Performance

```
GET /act_{ad_account_id}/ads

Fields per ad:
- id, name, status
- creative (link to creative asset)
- insights (nested performance data)
- adcreatives (actual creative content)
```

### Get Creative Breakdown

```
GET /{ad_id}/insights?breakdowns=creative

Shows which creative variations perform best.
```

---

## Implementation Plan

### Phase 1: Basic Connection (MVP)

1. **Backend: OAuth Service**
   - `/api/meta/auth/start` - Initiate OAuth flow
   - `/api/meta/auth/callback` - Handle OAuth callback
   - `/api/meta/auth/status` - Check connection status
   - Token storage with encryption

2. **Frontend: Connect Button**
   - "Connect Meta Ads" button in dashboard
   - Show connection status
   - Display connected ad accounts

3. **Data Fetch: Account Insights**
   - Fetch last 30 days performance
   - Store in database
   - Display in UI

### Phase 2: Ad-Level Analysis

1. **Match Ad Library → Performance**
   - Link Ad Library creative IDs to performance data
   - Show "This ad has 3.2% CTR" alongside creative

2. **Performance Dashboard**
   - Top performing ads by ROAS
   - Hook analysis with real data
   - Time-based trends

### Phase 3: Automated Insights

1. **Weekly Performance Reports**
   - Auto-generate insights
   - "Your question hooks have 2x higher CTR than statement hooks"

2. **Creative Recommendations**
   - Based on what's actually working
   - Not just what looks good

---

## Code Structure

```
backend/app/services/meta_ads/
├── __init__.py
├── oauth.py          # OAuth flow handling
├── client.py         # API client wrapper
├── insights.py       # Insights API calls
├── sync.py           # Data sync service
└── models.py         # MetaAdAccount model

backend/app/routers/
├── meta_auth.py      # OAuth endpoints

frontend/src/
├── pages/MetaConnect.tsx
├── components/AdPerformance.tsx
```

---

## Environment Variables

```env
# Meta App credentials
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_REDIRECT_URI=http://localhost:8000/api/meta/auth/callback

# Encryption for tokens
META_TOKEN_ENCRYPTION_KEY=your_32_byte_key
```

---

## Privacy & Security

### Client Concerns Addressed

1. **Data stays local**: Performance data stored in their database only
2. **Read-only access**: Only `ads_read`, no campaign modifications
3. **Revocable**: Users can disconnect anytime
4. **Encrypted**: Tokens encrypted at rest

### Compliance

- GDPR: User consent required
- Data retention: Clear policy on how long data is kept
- Access logs: Track who accessed what

---

## Cost Estimate

| Item | Cost |
|------|------|
| Meta API | Free (rate limited) |
| Development | ~20 hours |
| Token refresh cron | Minimal server cost |

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 | 1-2 days | OAuth + basic connection |
| Phase 2 | 2-3 days | Ad-level analysis |
| Phase 3 | 3-5 days | Automated insights |

---

## Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Implement caching, batch requests |
| Token expiry | Auto-refresh before expiry |
| Permission denial | Clear UI explaining why needed |
| Meta API changes | Abstract client layer |

---

## Next Steps

1. Register Meta App (requires business verification)
2. Implement OAuth service skeleton
3. Create database model for connected accounts
4. Build frontend connect flow
5. Test with sandbox ad account
