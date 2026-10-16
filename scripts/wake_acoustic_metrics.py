"""Test-only in-memory comparison of known WAV samples; never persists room PCM."""
import numpy as np


def split_stereo(pcm):
    if len(pcm)!=3200: raise ValueError('Expected 50 ms stereo S16LE at 16 kHz')
    values=np.frombuffer(pcm,dtype='<i2').reshape(-1,2)
    mixed=np.rint(values.astype(np.float64).mean(axis=1)).astype('<i2')
    return mixed.tobytes(),values[:,0].tobytes(),values[:,1].tobytes()


def alignment(reference, captured):
    """Peak absolute normalized correlation at original speed, with >= full clip.

    An acoustic match is evidence of signal transport, not speech intelligibility
    or wake acceptance. Return no score for absent/silent/short input.
    """
    ref=np.frombuffer(reference,dtype='<i2').astype(np.float64)
    got=np.frombuffer(captured,dtype='<i2').astype(np.float64)
    if len(ref)<160 or len(got)<len(ref): return {'correlation':None}
    ref-=ref.mean(); energy=float(np.dot(ref,ref))
    if energy<1: return {'correlation':None}
    n=1 << (len(ref)+len(got)-1).bit_length()
    dots=np.fft.irfft(np.fft.rfft(got,n)*np.fft.rfft(ref[::-1],n),n)[len(ref)-1:len(got)]
    sums=np.concatenate(([0.],np.cumsum(got)))
    squares=np.concatenate(([0.],np.cumsum(got*got)))
    window_energy=squares[len(ref):]-squares[:-len(ref)]-(sums[len(ref):]-sums[:-len(ref)])**2/len(ref)
    scores=np.abs(dots)/np.sqrt(energy*np.maximum(1.,window_energy))
    best=int(np.argmax(scores))
    return {'correlation':round(float(min(1.,scores[best])),4),'lag_seconds':round(best/16000,3)}
