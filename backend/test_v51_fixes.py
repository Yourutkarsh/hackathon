from risk_engine_v5_1 import *

# 1 Rule E: must fire from preliminary signals, not event['signals'].
event = {
    'timestamp_utc':'2026-01-01T10:00:00Z',
    'user_timezone':'UTC',
    'resource_family':'FINANCE',
    'sensitivity':'HIGH',
    'signals': {},
}
baseline = {'active_start_minute':480,'active_end_minute':1080,'resource_families':['ENG','FINANCE']}
prelim = {'LOCATION_NOVELTY':80,'DEVICE_NOVELTY':75,'APPLICATION_NOVELTY':71}
r = rule_detector(event, baseline, preliminary_signals=prelim)
assert r['rule_score'] == 100.0 or r['rule_score'] >= 25.0
assert r['rule_scores']['RULE_E_MULTI_FAMILY'] == 25.0
assert r['rule_available'] is True
missing_event = {'timestamp_utc': '2026-01-01T10:00:00Z'}
missing_baseline = {}
assert rule_detector(missing_event, missing_baseline)['rule_score'] is None
assert rule_detector(missing_event, missing_baseline)['rule_available'] is False

# 2 Missing rule input must not mark behavioral available.
rc = normalized_components(
    events=[{'timestamp_utc':'2026-01-01T10:00:00Z','event_id':'e1','user_id':'u1','signals':{}}],
    clusters=[], contexts=[]
)
assert rc.availability['behavioral_anomaly'] is False
assert rc.values['behavioral_anomaly'] == 0.0

# 3 Raw clusters and summaries must both work.
raw_events = [
 {'timestamp_utc':'2026-01-01T10:00:00Z','event_id':'e1','user_id':'u1','signals':{'LOCATION_NOVELTY':80}},
 {'timestamp_utc':'2026-01-01T10:10:00Z','event_id':'e2','user_id':'u1','signals':{'DEVICE_NOVELTY':70}},
]
clusters = cluster_events(raw_events)
summary = cluster_summaries(clusters)
assert temporal_component(clusters) == temporal_component(summary)

# 4 Same-timestamp events cannot serve as sensitivity history.
same_ts = [
 {'timestamp_utc':'2026-01-01T10:00:00Z','event_id':'a','user_id':'u1','resource_family':'FIN','sensitivity':'LOW'},
 {'timestamp_utc':'2026-01-01T10:00:00Z','event_id':'b','user_id':'u1','resource_family':'FIN','sensitivity':'CRITICAL'},
]
s, avail = sensitivity_component(same_ts)
assert s == 0.0 and avail is False, (s, avail)
# But a 30-day prior record should make it available even if outside 72h.
history = [
 {'timestamp_utc':'2025-12-10T10:00:00Z','event_id':'h','user_id':'u1','resource_family':'FIN','sensitivity':'LOW'},
]
s2, avail2 = sensitivity_component([same_ts[1]], resource_history=history)
assert avail2 is True and s2 == 100.0, (s2, avail2)

# 5 Context only discounts active targeted families.
ctx = [
 {'affected_signal_families':['LOCATION_NOVELTY'],'raw_reduction_points':50,'confidence':'HIGH'},
 {'affected_signal_families':['VOLUME_SPIKE'],'raw_reduction_points':100,'confidence':'HIGH'},
]
c, c_avail = context_component(ctx, ['LOCATION_NOVELTY'])
assert c == 50.0 and c_avail is True
c2, c2_avail = context_component(ctx, ['SENSITIVITY_INCREASE'])
assert c2 == 0.0 and c2_avail is False

# 6 IF q99==q95 fallback.
assert iforest_score(1.0, 1.0, 1.0) == 0.0
assert abs(iforest_score(1.000001, 1.0, 1.0) - 100.0) < 1e-6

print('ALL_TARGETED_TESTS_PASSED')
