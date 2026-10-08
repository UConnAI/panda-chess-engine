import hashlib,json,random
from pathlib import Path
import numpy as np
from engine.board import chess,board_state
from .model import Network,encode

ROOT=Path(__file__).resolve().parents[1]
class Trainer:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.dir=self.root/'models';self.dir.mkdir(exist_ok=True)
        blob=(ROOT/'data/positions.jsonl').read_bytes();self.provenance=json.loads((ROOT/'data/provenance.json').read_text())
        self.digest=hashlib.sha256(blob).hexdigest()
        if self.digest!=self.provenance['sha256']:raise ValueError('Teacher dataset checksum failed.')
        self.rows={s:[] for s in ('train','validation','test')}
        for line in blob.splitlines():
            r=json.loads(line);r['y']=float(np.tanh(r['cp']/400));r['x']=encode(chess.Board(r['fen']));self.rows[r['split']].append(r)
        random.Random(314).shuffle(self.rows['train'])
        self.current=None;self.net=None
        self.registry=json.loads((self.dir/'registry.json').read_text()) if (self.dir/'registry.json').exists() else dict(models=[],champion='positional',test_exposed=False)
        if self.registry['models']:self.load(self.registry['models'][-1]['id'])
    def save_registry(self):
        p=self.dir/'registry.tmp';p.write_text(json.dumps(self.registry,indent=2));p.replace(self.dir/'registry.json')
    def load(self,id):
        if id not in [r['id'] for r in self.registry['models']]:raise ValueError('Unknown saved network.')
        self.current=json.loads((self.dir/(id+'.json')).read_text());self.net=Network(self.current['parameters']);return self.status()
    def get_network(self,id):
        if id not in [r['id'] for r in self.registry['models']]:raise ValueError('Unknown saved network.')
        return Network(json.loads((self.dir/(id+'.json')).read_text())['parameters'])
    def delete_model(self,id,protected=()):
        record=next((r for r in self.registry['models'] if r['id']==id),None)
        if record is None:raise ValueError('Unknown saved network.')
        if id==self.registry['champion']:raise ValueError('The current champion cannot be deleted. Promote another model first.')
        if id in protected:raise ValueError('This model is used by an unfinished arena match. Finish it or prepare a different match first.')
        trash=self.dir/'.trash';trash.mkdir(exist_ok=True)
        source=self.dir/(id+'.json');target=trash/(id+'.json')
        if target.exists():raise ValueError('A deleted copy already exists; refusing to overwrite it.')
        old_models=self.registry['models'];old_deleted=self.registry.get('deleted_models',[])
        old_current,old_net=self.current,self.net
        source.rename(target)
        try:
            self.registry['models']=[r for r in old_models if r['id']!=id]
            self.registry['deleted_models']=old_deleted+[record]
            if self.current and self.current['id']==id:
                self.current=None;self.net=None
                if self.registry['models']:self.load(min(self.registry['models'],key=lambda r:r['validation']['mse'])['id'])
            self.save_registry()
        except Exception:
            self.registry['models']=old_models;self.registry['deleted_models']=old_deleted
            self.current,self.net=old_current,old_net;target.rename(source);raise
        return self.status()
    def restore_model(self,id):
        deleted=self.registry.get('deleted_models',[])
        record=next((r for r in deleted if r['id']==id),None)
        if record is None:raise ValueError('Unknown deleted network.')
        source=self.dir/'.trash'/(id+'.json');target=self.dir/(id+'.json')
        if target.exists():raise ValueError('A saved copy already exists; refusing to overwrite it.')
        old_models=self.registry['models']
        source.rename(target)
        try:
            self.registry['models']=old_models+[record]
            self.registry['deleted_models']=[r for r in deleted if r['id']!=id]
            self.save_registry()
        except Exception:
            self.registry['models']=old_models;self.registry['deleted_models']=deleted;target.rename(source);raise
        if not self.current:self.load(id)
        return self.status()
    def permanently_delete_model(self,id):
        deleted=self.registry.get('deleted_models',[])
        if not any(r['id']==id for r in deleted):raise ValueError('Only models in Deleted models can be permanently deleted.')
        source=self.dir/'.trash'/(id+'.json')
        old_number=self.registry.get('next_model_number')
        # Reserve legacy IDs even after their last file and metadata are erased.
        records=self.registry['models']+deleted
        self.registry['next_model_number']=max(old_number or 1,1+max(int(r['id'].split('-')[1]) for r in records))
        self.registry['deleted_models']=[r for r in deleted if r['id']!=id]
        try:
            self.save_registry()
            source.unlink()
        except Exception:
            self.registry['deleted_models']=deleted
            if old_number is None:self.registry.pop('next_model_number',None)
            else:self.registry['next_model_number']=old_number
            self.save_registry()
            raise
        return self.status()
    def metrics(self,split):
        rows=self.rows[split];pred,_=self.net.forward(np.array([r['x'] for r in rows]));y=np.array([r['y'] for r in rows]);return dict(mse=float(np.mean((pred-y)**2)),mae=float(np.mean(np.abs(pred-y))),n=len(rows))
    def train(self,count=800,epochs=10,rate=.01,resume=False):
        if type(count)is not int or count not in (200,800,1600,3199):raise ValueError('Unsupported sample count.')
        if type(epochs)is not int or epochs not in (1,10,30):raise ValueError('Choose 1, 10 or 30 epochs.')
        if type(rate)not in (int,float) or rate not in (.001,.005,.01):raise ValueError('Unsupported learning rate.')
        if type(resume)is not bool:raise ValueError('Resume must be boolean.')
        if resume and (not self.current or self.current['count']!=count or self.current['rate']!=rate):raise ValueError('Continue requires the same count/rate and a saved model.')
        if resume and self.current['epoch']+epochs>300:raise ValueError('300-epoch teaching limit reached.')
        if not resume:self.net=Network();self.current=dict(epoch=0,count=count,rate=rate,history=[])
        rows=self.rows['train'][:count];x=np.array([r['x'] for r in rows]);y=np.array([r['y'] for r in rows]);before=float(self.net.forward(x[:1])[0][0])
        def measure():
            p,_=self.net.forward(x);v=self.metrics('validation');return dict(epoch=self.current['epoch'],train_mse=float(np.mean((p-y)**2)),validation_mse=v['mse'])
        if not self.current['history']:self.current['history']=[measure()]
        for _ in range(epochs):
            # Full-batch gradient descent: one epoch is one exact gradient update.
            gradients=self.net.gradient(x,y)
            for k in gradients:self.net.p[k]-=rate*(gradients[k]+(.0002*self.net.p[k] if k in ('w','v') else 0))
            if not all(np.isfinite(v).all() for v in self.net.p.values()):raise ValueError('Nonfinite training result.')
            self.current['epoch']+=1;self.current['history'].append(measure())
        # Deleted IDs remain reserved so training cannot overwrite or reuse a version.
        records=self.registry['models']+self.registry.get('deleted_models',[])
        number=max(self.registry.get('next_model_number',1),1+max([0]+[int(r['id'].split('-')[1]) for r in records]))
        id=f"neural-{number:04d}";self.registry['next_model_number']=number+1
        self.current.update(id=id,parameters=self.net.json(),digest=self.digest,trace=dict(before=before,after=float(self.net.forward(x[:1])[0][0]),target=rows[0]['y'],teacher_cp=rows[0]['cp'],board=board_state(chess.Board(rows[0]['fen']))))
        path=self.dir/(id+'.json');path.write_text(json.dumps(self.current))
        self.registry['models'].append(dict(id=id,epoch=self.current['epoch'],count=count,rate=rate,validation=self.metrics('validation'),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        self.save_registry();return self.status()
    def status(self):
        result=dict(models=self.registry['models'],deleted_models=self.registry.get('deleted_models',[]),champion=self.registry['champion'],ready=self.current is not None,test_exposed=self.registry['test_exposed'],counts={k:len(v) for k,v in self.rows.items()},architecture='782 → 32 tanh → 1 tanh; 25,089 trainable parameters')
        for key,folder in (('models',self.dir),('deleted_models',self.dir/'.trash')):
            result[key]=[dict(r,size_bytes=(folder/(r['id']+'.json')).stat().st_size) for r in result[key]]
        personal=getattr(self,'personal',None)
        result['custom_bots']=personal.data['bots'] if personal else []
        if self.current:result.update({k:v for k,v in self.current.items() if k not in ('parameters',)});result['validation']=self.metrics('validation')
        return result
    def test(self):
        if not self.net:raise ValueError('Train or load a network first.')
        self.registry['test_exposed']=True;self.save_registry();return self.metrics('test')
