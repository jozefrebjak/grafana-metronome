#!/usr/bin/env python3
"""
Generates Grafana dashboard files for PowerDNS server statistics in the
current directory.
"""

import os
import sys
import json
import copy
import string


# Where to output the files
DIR = os.path.abspath(os.path.dirname(__file__))

DATASOURCE = "metronome"


class Dashboard:
    
    def __init__(self, title):
        self.data = {
            "___NOTE___": "AUTOMATICALLY GENERATED by dashboards/generate.py",
            "id": None,
            "title": title,
            "tags": ['pdns-default'],
            "style": "light",
            "timezone": "browser",
            "editable": True,
            "hideControls": False,
            "sharedCrosshair": True,
            "rows": [],
            "time": {
                "from": "now-6h",
                "to": "now"
            },
            "timepicker": {
                "refresh_intervals": [
                    "5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"
                ],
                "time_options": [
                    "5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"
                ]
            },
            "templating": {
                "list": []
            },
            "annotations": {
                "list": []
            },
            "refresh": False,
            "schemaVersion": 12,
            "version": 9,
            "links": [],
            "gnetId": None
        }
        self.last_id = 0

    def add_template_var(self, name, label, query, regex="", multi=False, include_all=False):
        self.data['templating']['list'].append({
            "current": {},
            "datasource": DATASOURCE,
            "hide": 0,
            "includeAll": include_all,
            "label": label,
            "multi": multi,
            "name": name,
            "options": [],
            "query": query,
            "refresh": 1,
            "regex": regex,
            "type": "query"
        })
    
    def add_template_var_choice(self, name, label, options, default=None, 
                                multi=False, include_all=False):
        options = map(str, options)
        if not default:
            default = options[0]
        else:
            default = str(default)

        options_list = [
            {
                "text": x,
                "value": x,
                "selected": x == default
            }
            for x in options
        ]
        options_str = ', '.join(options)

        self.data['templating']['list'].append({
            "type": "custom",
            "datasource": None,
            "refresh": 0,
            "name": "smoothing",
            "hide": 0,
            "options": options_list,
            "includeAll": include_all,
            "multi": multi,
            "query": options_str,
            "current": {
              "text": default,
              "value": default
            },
            "label": label,
        })

    def add_row(self, title, collapse=False, show_title=False):
        row = {
            "title": title,
            "collapse": collapse,
            "editable": True,
            "height": "250px",
            "panels": [],
            "showTitle": show_title,
        }
        self.data['rows'].append(row)

    def add_graph(self, title, targets, stack=False, span=12,
                  y_min=0, y_max=None, y_format='short'):
        assert isinstance(targets, list)
        panel = {
           "title": title,
           "datasource": DATASOURCE,
           "aliasColors": {},
           "bars": False,
           "editable": True,
           "error": False,
           "fill": 1,
           "grid": {
             "threshold1": None,
             "threshold1Color": "rgba(216, 200, 27, 0.27)",
             "threshold2": None,
             "threshold2Color": "rgba(234, 112, 112, 0.22)"
           },
           "id": self._next_id(),
           "isNew": True,
           "legend": {
             "avg": False,
             "current": False,
             "max": False,
             "min": False,
             "show": True,
             "total": False,
             "values": False
           },
           "lines": True,
           "linewidth": 2,
           "links": [],
           "nullPointMode": "zero" if stack else "null",
           "percentage": False,
           "pointradius": 5,
           "points": False,
           "renderer": "flot",
           "seriesOverrides": [],
           "span": span,
           "stack": stack,
           "steppedLine": False,
           "targets": [
             { "hide": False, "refId": string.ascii_uppercase[i], "target": x } 
             for i, x in enumerate(targets)
           ],
           "timeFrom": None,
           "timeShift": None,
           "tooltip": {
             "msResolution": False,
             "shared": True,
             "sort": 0,
             "value_type": "cumulative"
           },
           "type": "graph",
           "xaxis": {
             "show": True
           },
           "yaxes": [
             {
               "format": y_format,
               "label": None,
               "logBase": 1,
               "max": y_max,
               "min": y_min,
               "show": True
             },
             {
               "format": "short",
               "label": None,
               "logBase": 1,
               "max": None,
               "min": None,
               "show": True
             }
           ]
        }
        self.data['rows'][-1]['panels'].append(panel)

    def add_annotation(self, name, target):
        self.data['annotations']['list'].append({
            "name": name,
            "datasource": DATASOURCE,
            "iconColor": "rgba(255, 96, 96, 1)",
            "enable": True,
            "target": target
            #"target": "alias(removeAboveValue(derivative(dnsdist.$dnsdist.main.uptime_dt), -1), 'server restart')"
        })

    def add_graph_row(self, title, targets, collapse=False, **graph_options):
        assert isinstance(targets, list)
        self.add_row(title, collapse=collapse)
        self.add_graph(title, targets, **graph_options)
    
    def save(self, fpath):
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(
                self.data, f, indent=2, ensure_ascii=False, sort_keys=True)

    def _next_id(self):
        self.last_id += 1
        return self.last_id


def compact(s):
    return ' '.join( x.strip() for x in s.split('\n') ).strip()


dnsdist = Dashboard(title="PowerDNS dnsdist [default]")
dnsdist.add_template_var(
    name='dnsdist', label='dnsdist server', query='dnsdist.*', multi=False)
dnsdist.add_template_var_choice(
    name='smoothing', label='smoothing (moving average)', multi=False,
    options=[1, 3, 5, 7, 10, 15, 20, 30, 50, "'5min'", "'10min'", "'30min'", "'1hour'"], default=5)

dnsdist.add_graph_row(
    title='Number of queries',
    targets=[
        "alias(movingAverage(dnsdist.$dnsdist.main.servfail-responses_dt, $smoothing), 'Servfail/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.queries_dt, $smoothing), 'Queries/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.responses_dt, $smoothing), 'Responses/s')",
    ],
)

dnsdist.add_row('Latency')
dnsdist.add_graph(
    title='Latency (answers/s in a latency band)',
    span=6,
    targets=[
        "alias(movingAverage(dnsdist.$dnsdist.main.latency0-1_dt, $smoothing), '<1 ms')",
        "alias(movingAverage(dnsdist.$dnsdist.main.latency1-10_dt, $smoothing), '<10 ms')",
        "alias(movingAverage(dnsdist.$dnsdist.main.latency10-50_dt, $smoothing), '<50 ms')",
        "alias(movingAverage(dnsdist.$dnsdist.main.latency50-100_dt, $smoothing), '<100 ms')",
        "alias(movingAverage(dnsdist.$dnsdist.main.latency100-1000_dt, $smoothing), '<1000 ms')",
        "alias(movingAverage(dnsdist.$dnsdist.main.latency-slow_dt, $smoothing), 'With slow answers')",
    ],
    stack=True
)
dnsdist.add_graph(
    title='Average latency',
    span=6,
    y_format='µs',
    targets=[
        "alias(dnsdist.$dnsdist.main.latency-avg100, '100 packet average')",
        "alias(dnsdist.$dnsdist.main.latency-avg10000, '10,000 packet average')",
        "alias(dnsdist.$dnsdist.main.latency-avg1000000, '1,000,000 packet average')",
    ],
)

dnsdist.add_row('Queries drops and policy')
dnsdist.add_graph(
    title='Query drops',
    span=6,
    targets=[
        "alias(movingAverage(dnsdist.$dnsdist.main.rule-drop_dt, $smoothing), 'Rule drops/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.acl-drops_dt, $smoothing), 'ACL drops/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.dyn-blocked_dt, $smoothing), 'Dynamic drops/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.block-filter_dt, $smoothing), 'Blockfilter drops/s')",
    ],
)
dnsdist.add_graph(
    title='Query policy',
    span=6,
    targets=[
        "alias(movingAverage(dnsdist.$dnsdist.main.rdqueries_dt, $smoothing), 'RD Queries/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.rule-nxdomain_dt, $smoothing), 'Rule NXDomain/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.self-answered_dt, $smoothing), 'Rule self-answered/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.no-policy_dt, $smoothing), 'No policy/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.noncompliant-queries_dt, $smoothing), 'Non-compliant queries/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.noncompliant-responses_dt, $smoothing), 'Non-compliant responses/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.empty-queries_dt, $smoothing), 'Empty queries/s')",
    ],
)

dnsdist.add_row('Timeouts, errors and cache miss rate')
dnsdist.add_graph(
    title='Timeouts and errors',
    span=6,
    targets=[
        "alias(movingAverage(dnsdist.$dnsdist.main.downstream-timeouts_dt, $smoothing), 'Timeouts/s')",
        "alias(movingAverage(dnsdist.$dnsdist.main.downstream-send-errors_dt, $smoothing), 'Errors/s')",
    ],
)
# TODO: filter out small values? Now a single miss will show as 100%
dnsdist.add_graph(
    title='Cache miss rate',
    span=6,
    y_format='percentunit',
    targets=[
        compact("""
        alias(movingAverage(
            divideSeries(
                dnsdist.$dnsdist.main.cache-misses_dt,
                sumSeries(
                    dnsdist.$dnsdist.main.cache-misses_dt, 
                    dnsdist.$dnsdist.main.cache-hits_dt
                )
            )
        , $smoothing), 'cache miss rate (%)')
        """)
    ],
)

dnsdist.add_row('CPU and memory usage')
dnsdist.add_graph(
    title='CPU usage',
    span=6,
    y_format='percent',
    stack=True,
    targets=[
        "alias(scale(movingAverage(dnsdist.$dnsdist.main.cpu-sys-msec_dt, $smoothing), 0.1), 'System CPU')",
        "alias(scale(movingAverage(dnsdist.$dnsdist.main.cpu-user-msec_dt, $smoothing), 0.1), 'Total (system+user) CPU')",
    ],
)

dnsdist.add_graph(
    title='Memory usage',
    span=6,
    y_format='bytes',
    targets=[
        "alias(dnsdist.$dnsdist.main.real-memory-usage, 'Memory usage')",
    ],
)

dnsdist.add_row('File descriptors, uptime and dynamic block size')
dnsdist.add_graph(
    title='File descriptor usage',
    span=4,
    targets=[
        "alias(dnsdist.$dnsdist.main.fd-usage, 'Number of file descriptors')",
    ],
)
dnsdist.add_graph(
    title='Uptime',
    y_format='s',
    span=4,
    targets=[
        "alias(dnsdist.$dnsdist.main.uptime, 'Uptime')",
    ],
)
dnsdist.add_graph(
    title='Dynamic block size',
    span=4,
    targets=[
        "alias(dnsdist.$dnsdist.main.dyn-block-nmg-size, 'Number of entries')",
    ],
)

dnsdist.add_row('Per server statistics', collapse=True, show_title=True)
#dnsdist.add_row('Queries and latency per server')
dnsdist.add_graph(
    title='Queries/s per server',
    span=6,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.servers.*.queries_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Latency per server',
    y_format='µs',
    span=6,
    targets=[
        "aliasByNode(dnsdist.$dnsdist.main.servers.*.latency, 4)",
    ],
)

#dnsdist.add_row('Drops, send errors and outstanding per server')
dnsdist.add_graph(
    title='Drops/s per server',
    span=4,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.servers.*.drops_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Send errors/s per server',
    span=4,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.servers.*.senderrors_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Outstanding per server',
    span=4,
    targets=[
        "aliasByNode(dnsdist.$dnsdist.main.servers.*.outstanding, 4)",
    ],
)

dnsdist.add_row('Per pool statistics', collapse=True, show_title=True)
#dnsdist.add_row('Servers and cache size per pool')
dnsdist.add_graph(
    title='Servers per pool',
    span=4,
    targets=[
        "aliasByNode(dnsdist.$dnsdist.main.pools.*.servers, 4)",
    ],
)
dnsdist.add_graph(
    title='Cache size per pool (max number of entries)',
    span=4,
    targets=[
        "aliasByNode(dnsdist.$dnsdist.main.pools.*.cache-size, 4)",
    ],
)
dnsdist.add_graph(
    title='Cache size per pool (current number of entries)',
    span=4,
    targets=[
        "aliasByNode(dnsdist.$dnsdist.main.pools.*.cache-entries, 4)",
    ],
)

#dnsdist.add_row('Cache hits/misses per pool')
dnsdist.add_graph(
    title='Cache hits per pool',
    span=6,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.pools.*.cache-hits_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Cache misses per pool',
    span=6,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.pools.*.cache-misses_dt, $smoothing), 4)",
    ],
)

#dnsdist.add_row('Cache deferred and collisions per pool')
dnsdist.add_graph(
    title='Cache deferred inserts per pool',
    span=3,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.pools.*.cache-deferred-inserts_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Cache deferred lookups per pool',
    span=3,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.pools.*.cache-deferred-lookups_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Cache insert collisions per pool',
    span=3,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.pools.*.cache-insert-collisions_dt, $smoothing), 4)",
    ],
)
dnsdist.add_graph(
    title='Cache lookup collisions per pool',
    span=3,
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.pools.*.cache-lookup-collisions_dt, $smoothing), 4)",
    ],
)

dnsdist.add_row('Per frontend statistics', collapse=True, show_title=True)
dnsdist.add_graph(
    # TODO: test this one
    title='Queries/s per frontend',
    targets=[
        "aliasByNode(movingAverage(dnsdist.$dnsdist.main.frontends.*.queries_dt, $smoothing), 4)",
    ],
)

dnsdist.add_annotation(
    name='dnsdist restart', 
    target="alias(removeAboveValue(derivative(dnsdist.$dnsdist.main.uptime), -10), 'dnsdist restart')"
)

dnsdist.save(os.path.join(DIR, 'dnsdist.json'))


