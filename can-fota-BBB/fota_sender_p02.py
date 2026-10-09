"""P02 F407 sender core: deterministic DATA omissions and bounded protocol waits."""
import argparse, os, socket, struct, time, zlib
from fota_p01 import Metrics, standard_data_id
from fota_p02 import LossModel, DeadlineExceeded, append_jsonl, append_result, require_deadline, sha256_file, utc_now

CUSTOM_CMD,CUSTOM_RESP,ISO_CMD,ISO_RESP=0x100,0x101,0x7e0,0x7e8
FOTA_ENTRY_CMD=0x200
def frame(ident,payload):
 data=bytes(payload);return struct.pack('<IB3x8s',ident,len(data),data+b'\0'*(8-len(data)))
def recv(bus,timeout):
 bus.settimeout(timeout)
 try:return bus.recv(16)
 except (socket.timeout,BlockingIOError):return None
def tx(bus,ident,payload,m,deadline,**kw):return m.attempt_send(bus,frame(ident,payload),deadline=deadline,**kw)
def enter_bootloader(bus,a):
 bus.send(frame(FOTA_ENTRY_CMD,[0xde,0xad]))
 time.sleep(a.entry_wait_sec)
 bus.setblocking(False)
 try:
  while bus.recv(16):pass
 except (BlockingIOError,OSError):pass
 finally:bus.setblocking(True)
def custom_rx(bus,m,t):
 raw=recv(bus,t)
 if not raw:return None
 ident,dlc,data=struct.unpack('<IB3x8s',raw);kind=data[0]>>6
 if standard_data_id(ident,CUSTOM_RESP) and ((kind in(0,2) and dlc==2) or(kind==1 and dlc==8)):
  m.protocol_rx+=1;return kind,(int.from_bytes(data[1:8],'little') if kind==1 else data[0]&63)
 m.invalid_protocol_rx+=1;return None
def iso_rx(bus,m,cmd,t,fc=False):
 raw=recv(bus,t)
 if not raw:return None
 ident,dlc,data=struct.unpack('<IB3x8s',raw)
 if not standard_data_id(ident,ISO_RESP) or dlc!=8:m.invalid_protocol_rx+=1;return None
 if fc:
  good=data[:3]==b'\x30\x08\x00';m.protocol_rx+=bool(good);m.invalid_protocol_rx+=not good;return good
 length=data[0]&15;good=(data[0]>>4)==0 and length>=2 and data[1]==cmd
 m.protocol_rx+=bool(good);m.invalid_protocol_rx+=not good;return data[1:1+length] if good else None
def custom(bus,fw,m,loss,deadline,a):
 start=time.monotonic()
 if not tx(bus,CUSTOM_CMD,[0x40]+list(len(fw).to_bytes(4,'little')),m,deadline):return 'FAIL_ENOBUFS',start
 if custom_rx(bus,m,a.start_timeout)!=(0,0):return 'FAIL_START',start
 for block,off in enumerate(range(0,len(fw),256)):
  parts=[(s//7,list(fw[off+s:off+s+7]))for s in range(0,len(fw[off:off+256]),7)]
  for index,(seq,data) in enumerate(parts):
   drop=loss.drop('custom_data',block,index)
   if not tx(bus,CUSTOM_CMD,[seq]+data,m,deadline,dropped=drop) and not drop:return 'FAIL_ENOBUFS',start
  reply=custom_rx(bus,m,a.data_timeout)
  # The target emits a bitmap NACK only after it sees the final DATA frame.
  # Probe that frame again if it was omitted, but keep recovery finite.
  probes=0
  while not reply and probes<a.max_custom_probe_attempts:
   seq,data=parts[-1];drop=loss.drop('custom_data',block,len(parts)-1,True)
   if not tx(bus,CUSTOM_CMD,[seq]+data,m,deadline,dropped=drop,retransmit=True) and not drop:return 'FAIL_ENOBUFS',start
   probes+=1;reply=custom_rx(bus,m,a.data_timeout)
  if reply==(0,0):continue
  if not reply:return 'FAIL_DATA_TIMEOUT',start
  if reply[0]!=1:return 'FAIL_TARGET' if reply[0]==2 else 'FAIL_DATA_RESPONSE',start
  missing=[i for i in range(len(parts)) if not reply[1]&(1<<i)]
  if not missing:return 'FAIL_DATA_RESPONSE',start
  for i in missing:
   seq,data=parts[i];drop=loss.drop('custom_data',block,i,True)
   if not tx(bus,CUSTOM_CMD,[seq]+data,m,deadline,dropped=drop,retransmit=True) and not drop:return 'FAIL_ENOBUFS',start
  if custom_rx(bus,m,a.data_timeout)!=(0,0):return 'FAIL_DATA_RETRY',start
 crc=zlib.crc32(fw)&0xffffffff
 if not tx(bus,CUSTOM_CMD,[0x80]+list(crc.to_bytes(4,'little')),m,deadline):return 'FAIL_ENOBUFS',start
 return ('OK' if custom_rx(bus,m,a.end_timeout)==(0,0) else 'FAIL_END_CRC'),start
def iso_chunk(bus,payload,block,m,loss,deadline,a,retry):
 plen=len(payload);ff=bytearray(8);ff[0]=0x10|(plen>>8);ff[1]=plen&255;ff[2:]=payload[:6]
 if not tx(bus,ISO_CMD,ff,m,deadline,retransmit=retry) or not iso_rx(bus,m,0,a.fc_timeout,True):return False
 pos,seq=6,1
 while pos<plen:
  require_deadline(deadline,'DATA');part=payload[pos:pos+7];cf=bytearray(8);cf[0]=0x20|(seq&15);cf[1:1+len(part)]=part
  drop=loss.drop('isotp_cf',block,seq,retry)
  if not tx(bus,ISO_CMD,cf,m,deadline,dropped=drop,retransmit=retry) and not drop:return False
  pos+=len(part);seq=(seq+1)&15
  if seq%8==1 and pos<plen and not iso_rx(bus,m,0,a.fc_timeout,True):return False
 return True
def iso(bus,fw,m,loss,deadline,a):
 start=time.monotonic();tx(bus,ISO_CMD,[5,0x10]+list(len(fw).to_bytes(4,'little')),m,deadline);ack=iso_rx(bus,m,0x10,a.start_timeout)
 if not ack or ack[1]:return 'FAIL_START',start
 size=int.from_bytes(ack[2:4],'little') or 256
 for block,off in enumerate(range(0,len(fw),size)):
  ok=False
  for retry in range(a.max_block_attempts):
   if iso_chunk(bus,bytes([0x20])+fw[off:off+size],block,m,loss,deadline,a,bool(retry)):
    ack=iso_rx(bus,m,0x20,a.data_timeout);ok=bool(ack and ack[1]==0)
   if ok:break
  if not ok:return 'FAIL_DATA_RETRY',start
 crc=zlib.crc32(fw)&0xffffffff;tx(bus,ISO_CMD,[5,0x30]+list(crc.to_bytes(4,'little')),m,deadline);ack=iso_rx(bus,m,0x30,a.end_timeout)
 return ('OK' if ack and ack[1]==0 else 'FAIL_END_CRC'),start
def main(protocol):
 p=argparse.ArgumentParser();p.add_argument('--firmware',required=True);p.add_argument('--run-dir',required=True);p.add_argument('--attempt-id',required=True);p.add_argument('--loss',type=float,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--transaction-timeout',type=float,default=120);p.add_argument('--max-block-attempts',type=int,default=4);p.add_argument('--max-custom-probe-attempts',type=int,default=4);p.add_argument('--can-interface',default='can0');p.add_argument('--entry-wait-sec',type=float,default=3.0);a=p.parse_args()
 if not 0<=a.loss<=1 or a.transaction_timeout<=0 or a.max_block_attempts<1 or a.max_custom_probe_attempts<1 or a.entry_wait_sec<0:raise SystemExit('invalid bounded configuration')
 a.start_timeout,a.data_timeout,a.end_timeout,a.fc_timeout=15,.15,3,1;fw=open(a.firmware,'rb').read();m=Metrics();loss=LossModel(a.seed,a.loss);begun=None;status,stage,boot='FAIL_SOCKET','SOCKET','NOT_ATTEMPTED'
 try:
  bus=socket.socket(socket.AF_CAN,socket.SOCK_RAW,socket.CAN_RAW);bus.bind((a.can_interface,));stage='ENTRY';enter_bootloader(bus,a);begun=time.monotonic();stage='START';status,start=(custom if protocol=='Custom' else iso)(bus,fw,m,loss,begun+a.transaction_timeout,a);stage='END' if status=='OK' else status[5:]
  if status=='OK':
   try:bus.send(frame(CUSTOM_CMD if protocol=='Custom' else ISO_CMD,[0xc0] if protocol=='Custom' else [2,0x40,0]));boot='JUMP_SENT_NOT_VERIFIED'
   except OSError:status,stage='FAIL_JUMP_SEND','JUMP'
 except DeadlineExceeded as e:status,stage='FAIL_TRANSACTION_TIMEOUT',str(e)
 except KeyboardInterrupt:status='INTERRUPTED'
 except OSError:status='FAIL_SOCKET' if stage=='SOCKET' else ('FAIL_ENTRY_SEND' if stage=='ENTRY' else 'FAIL_SEND')
 elapsed=0 if begun is None else time.monotonic()-begun
 row={'attempt_id':a.attempt_id,'timestamp_utc':utc_now(),'protocol':protocol,'loss_rate':a.loss,'seed':a.seed,'firmware_sha256':sha256_file(a.firmware),'transaction_status':status,'boot_status':boot,'failure_stage':stage,'elapsed_sec':f'{elapsed:.6f}','send_attempts':m.send_attempts,'software_drops':m.software_drops,'socket_send_success':m.socket_send_success,'send_errors':m.send_errors,'protocol_rx':m.protocol_rx,'invalid_protocol_rx':m.invalid_protocol_rx,'retransmit_attempts':m.retransmit_attempts,'retransmit_send_success':m.retransmit_send_success,'drop_events_json':loss.events,'note':f'entry 0x200#DEAD, wait {a.entry_wait_sec}s excluded; overhead denominator: all send_attempts'}
 append_result(os.path.join(a.run_dir,'raw.csv'),row);append_jsonl(os.path.join(a.run_dir,'events.jsonl'),row);return status!='OK'
