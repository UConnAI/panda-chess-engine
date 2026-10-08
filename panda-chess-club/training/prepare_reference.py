"""Prepare a reproducible reference with the SAME 782 -> 32 -> 1 network.

Run before the demo: python -m training.prepare_reference
Validation selects the checkpoint; test boards are measured once afterward.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,copy,hashlib,json,time
from pathlib import Path
import numpy as np
from training.train import Trainer,ROOT
from training.model import Network

def prepare(output=ROOT/'references'/'prepared.json',max_epochs=2000,patience=200):
    started=time.perf_counter()
    # Temporary training state stays outside members' saved-model registry.
    import tempfile
    (ROOT/'.build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
        t=Trainer(folder);net=Network();t.net=net
        x=np.array([r['x'] for r in t.rows['train']]);y=np.array([r['y'] for r in t.rows['train']])
        initial=t.metrics('validation');best=initial['mse'];best_parameters=copy.deepcopy(net.json())
        best_epoch=0;history=[];m={k:np.zeros_like(v) for k,v in net.p.items()};v=copy.deepcopy(m)
        for epoch in range(1,max_epochs+1):
            gradients=net.gradient(x,y)
            for k,g in gradients.items():
                if k in ('w','v'):g=g+.0002*net.p[k]
                m[k]=.9*m[k]+.1*g;v[k]=.999*v[k]+.001*g*g
                net.p[k]-=.003*(m[k]/(1-.9**epoch))/(np.sqrt(v[k]/(1-.999**epoch))+1e-8)
            validation=t.metrics('validation')
            if epoch%10==0 or epoch==1:
                prediction,_=net.forward(x)
                history.append(dict(epoch=epoch,train_mse=float(np.mean((prediction-y)**2)),validation_mse=validation['mse']))
            if validation['mse']<best-1e-7:
                best=validation['mse'];best_epoch=epoch;best_parameters=copy.deepcopy(net.json())
            if epoch-best_epoch>=patience:break
        t.net=Network(best_parameters)
        result=dict(id='reference-neural',architecture='782 → 32 tanh → 1 tanh',seed=314,
                    optimizer='Adam',rate=.003,count=len(x),epoch=best_epoch,epochs_run=epoch,
                    max_epochs=max_epochs,patience=patience,initial_validation=initial,
                    validation=t.metrics('validation'),test=t.metrics('test'),history=history,
                    seconds=round(time.perf_counter()-started,2),digest=t.digest,
                    selection='Lowest validation MSE; test split measured once after selection.',
                    parameters=best_parameters)
        output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result),encoding='utf-8')
        report={k:v for k,v in result.items() if k not in ('parameters','history')}
        report['sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
        print(json.dumps(report,indent=2),flush=True)
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'references'/'prepared.json')
    args=p.parse_args();prepare(args.output)
