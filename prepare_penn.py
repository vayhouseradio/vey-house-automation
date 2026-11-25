from pathlib import Path
import xml.etree.ElementTree as E,email.utils,subprocess,re,json,hashlib
out=Path('output');(out/'mix').mkdir(parents=True,exist_ok=True)
subprocess.run(['curl','--fail','--location','--retry','3','--max-time','60','https://www.music-zone.es/PodcastDP/UrbanaRS.xml','-o','urbana.xml'],check=True)
items=E.parse('urbana.xml').getroot().findall('./channel/item');item=max(items,key=lambda i:email.utils.parsedate_to_datetime(i.findtext('pubDate')))
source=item.find('enclosure').attrib['url'];url=source.replace('https://dts.podtrac.com/redirect.m4a/','https://');assert re.fullmatch(r'https://www\.music-zone\.es/PodcastDP/UrbanaRS\d+\.m4a',url)
ff='ffmpeg';original=out.parent/'penn-source.m4a'
subprocess.run(['curl','-fL','--max-time','120',url,'-o',str(original)],check=True)
target=out/'converted.mp3'
subprocess.run([ff,'-v','error','-y','-i',str(original),'-vn','-map_metadata','-1','-af','loudnorm=I=-14:TP=-2:LRA=11','-ar','44100','-ac','2','-c:a','libmp3lame','-b:a','192k','-write_xing','0','-id3v2_version','0',str(target)],check=True)
data=target.read_bytes();key='mix/'+hashlib.sha256(data).hexdigest()[:24]+'.mp3';target.rename(out/key);offset=frames=0;points=[]
while offset+4<=len(data):
 h=int.from_bytes(data[offset:offset+4],'big');assert h&0xfffe0000==0xfffa0000
 rate=(44100,48000,32000)[h>>10&3];bit=(0,32,40,48,56,64,80,96,112,128,160,192,224,256,320)[h>>12&15];assert rate==44100 and bit==192
 if frames%300==0:points.append(offset)
 offset+=144000*bit//rate+(h>>9&1);frames+=1
assert offset==len(data);seconds=frames*1152/44100;assert 3300<=seconds<=3900
record={'title':item.findtext('title'),'artist':'David Penn','url':'https://vey-house-audio.vayhouseradio.workers.dev/'+key,'sourceUrl':source,'publishedAt':int(email.utils.parsedate_to_datetime(item.findtext('pubDate')).timestamp()*1000),'seconds':seconds,'library':[[key,44100,len(data),points]]}
(out/'david-penn.json').write_text(json.dumps(record,separators=(',',':')));print(json.dumps({'key':key,'title':record['title'],'seconds':seconds}),flush=True)

# Publish audio first; changing the manifest is the final commit.
import os,boto3
client=boto3.client('s3',endpoint_url=os.environ['R2_ENDPOINT'],aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],region_name='auto')
bucket='vey-house-audio'
client.upload_file(str(out/key),bucket,key,ExtraArgs={'ContentType':'audio/mpeg'})
assert client.head_object(Bucket=bucket,Key=key)['ContentLength']==len(data)
client.upload_file(str(out/'david-penn.json'),bucket,'david-penn.json',ExtraArgs={'ContentType':'application/json','CacheControl':'no-cache'})
print('Published David Penn episode and verified audio size.')
