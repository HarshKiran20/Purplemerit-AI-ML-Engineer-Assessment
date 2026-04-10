# PurpleMerit — Smart Rewards Dashboard
## Release Notes v2.4.0 | Launch Day: Day 8

---

## Feature Overview
The Smart Rewards Dashboard is a complete overhaul of PurpleMerit's loyalty and rewards system.
It introduces AI-powered personalized reward recommendations, a gamified streak system, a richer
rewards catalog (3x more items), and a new real-time points ledger.

## Key Changes
- **New rewards catalog**: Expanded from 40 to 120 reward items with dynamic pricing
- **Personalization engine**: ML model serving reward recommendations per user segment
- **Streak system**: Daily engagement streaks with bonus multipliers
- **Real-time ledger**: Points balance now updates in real-time (previously batch updated every 24h)
- **New payment gateway**: Migrated from PayGate v1 to PayGate v2 for faster processing
- **UI redesign**: Full redesign of the rewards tab using new design system components

## Rollout Strategy
- Day 8: 20% of users (canary release)
- Day 10: 50% of users (if metrics hold)
- Day 12: 100% of users (full rollout)

## Success Criteria (defined pre-launch)
- Activation conversion: must stay >= 60% (baseline 62%)
- Crash rate: must stay <= 1.0% (baseline 0.8%)
- API latency p95: must stay <= 300ms (baseline 210ms)
- Payment success rate: must stay >= 97% (baseline 97.5%)
- Support ticket volume: must stay <= 60/day (baseline 45/day)
- D1 retention: must stay >= 53% (baseline 55%)
- Feature adoption funnel: must stay >= 45% (baseline 48%)

## Known Risks (Pre-launch)
1. **Payment gateway migration**: PayGate v2 is new and untested at scale. Load testing was done
   only up to 500 concurrent users; production peak is ~2,000 concurrent users.
2. **Personalization model latency**: The ML recommendation model adds ~80-120ms to page load.
   Under high load this could degrade p95 latency significantly.
3. **Real-time ledger sync**: Switching from batch to real-time point updates introduces potential
   race conditions if multiple transactions occur simultaneously.
4. **Android compatibility**: The new design system components have only been tested on Android 12
   and 13. Android 14 compatibility was not fully validated.
5. **Data migration**: Existing user reward histories were migrated to a new schema. Edge cases
   with legacy accounts (pre-2021) were not fully tested.

## Rollback Plan
- Feature flag: `REWARDS_V2_ENABLED` can be toggled off in 5 minutes
- PayGate v2 → v1 rollback: requires 30-minute maintenance window
- Data migration rollback: NOT available (one-way schema migration)
- Estimated full rollback time: 35-40 minutes

## Team
- PM: Priya Sharma
- Engineering Lead: Arjun Mehta
- Data: Kavya Nair
- Marketing: Rohan Verma
- QA Lead: Sneha Patel