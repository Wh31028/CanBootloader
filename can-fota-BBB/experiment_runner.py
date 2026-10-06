#!/usr/bin/env python3
"""Append-only P02 runner. It schedules trials but never configures CAN or flashes a board."""
import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()
def write_json(path, value):
    with open(path,'w',encoding='utf-8') as f: json.dump(value,f,indent=2,sort_keys=True); f.write('\n')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True); p.add_argument('--run-dir',required=True)
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args(); cfg=json.load(open(a.config,encoding='utf-8'))
    if os.path.exists(a.run_dir): raise SystemExit('run-dir must be a new unique path')
    required = {'firmware_path', 'firmware_sha256', 'bootloader_sha256', 'host_source_fingerprint', 'planned_trials', 'runner_timeout_sec'}
    missing = required - set(cfg)
    if missing: raise SystemExit('missing frozen config fields: ' + ', '.join(sorted(missing)))
    os.makedirs(a.run_dir); manifest={'schema':'p02-run-manifest-v1','created_utc':datetime.now(timezone.utc).isoformat(),'config':cfg,'trials':[]}
    write_json(os.path.join(a.run_dir,'manifest.json'),manifest)
    for trial in cfg['planned_trials']:
        attempt=trial['attempt_id']; protocol=trial['protocol']
        if protocol not in ('Custom', 'RAW_ISO-TP'): raise SystemExit('unsupported protocol: ' + protocol)
        script=os.path.join(os.path.dirname(__file__), 'loss_test_custom.py' if protocol=='Custom' else 'loss_test_isotp_raw.py')
        command=[sys.executable,script,'--run-dir',a.run_dir,'--attempt-id',attempt,'--loss',str(trial['loss_rate']),'--seed',str(trial['seed']),'--firmware',cfg['firmware_path']]
        record={'attempt_id':attempt,'protocol':protocol,'command':command,'state':'PLANNED',
                'firmware_sha256':cfg['firmware_sha256'],'bootloader_sha256':cfg['bootloader_sha256'],
                'host_source_fingerprint':cfg['host_source_fingerprint']}
        manifest['trials'].append(record); write_json(os.path.join(a.run_dir,'manifest.json'),manifest)
        if a.dry_run: record.update(state='DRY_RUN',exit_code=None); write_json(os.path.join(a.run_dir,'manifest.json'),manifest); continue
        try: result=subprocess.run(command,timeout=cfg['runner_timeout_sec'],check=False)
        except subprocess.TimeoutExpired: record.update(state='RUNNER_KILLED',exit_code=None)
        else: record.update(state='EXITED',exit_code=result.returncode)
        write_json(os.path.join(a.run_dir,'manifest.json'),manifest)
if __name__=='__main__': main()
