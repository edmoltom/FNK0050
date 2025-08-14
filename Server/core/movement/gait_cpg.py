import math
import numpy as np

def _clip(x, a, b): 
    return max(a, min(b, x))

class CPG:
    def __init__(self, gait="walk"):
        self.phi = [0.0, 0.25, 0.5, 0.75]
        self.freq = 0.8; self.amp_xy = 1.0; self.amp_z = 1.0
        self.set_gait(gait)

        # targets + estados con rampa
        self.freq_tgt = self.freq;     self.freq_cur = self.freq
        self.amp_xy_tgt = self.amp_xy; self.amp_xy_cur = self.amp_xy
        self.amp_z_tgt  = self.amp_z;  self.amp_z_cur  = self.amp_z
        self.duty_tgt   = self.duty;   self.duty_cur   = self.duty
        self.tau = 0.25  # s (constante de tiempo de las rampas)

    def set_gait(self, gait):
        self.phase_offsets = [0.0, 0.25, 0.5, 0.75]
        self.duty = 0.65
        self.gait = gait

    def set_velocity(self, vx, vy, wz):
        # magnitud “demanda”
        s = math.hypot(vx, vy) + 0.3 * abs(wz)

        if s <= 1e-6:
            self.freq_tgt = 0.0
            self.amp_xy_tgt = 0.0
            self.amp_z_tgt = 0.0
            self.duty_tgt = max(0.75, min(0.80, 0.80 - 0.25*sn))
            return    

        # Normaliza s a [0..1] para el duty adaptativo
        sn = max(0.0, min(1.0, s / 1.5))

        # Objetivos con límites seguros
        self.freq_tgt   = max(0.2, min(2.0, 0.6 + 1.4 * s))
        self.amp_xy_tgt = max(0.0, min(1.5, 0.6 + 1.2 * s))
        self.amp_z_tgt  = max(0.0, min(1.2, 0.5 + 0.7 * s))
        # MÁS APOYO: duty mínimo 0.75
        self.duty_tgt   = max(0.75, min(0.80, 0.80 - 0.25 * sn))

    def update(self, dt):
        if dt <= 0: 
            return [(self.phi[i] + self.phase_offsets[i]) % 1.0 for i in range(4)]

        # rampa exponencial
        alpha = 1.0 - math.exp(-dt / self.tau)
        self.freq_cur   += alpha * (self.freq_tgt   - self.freq_cur)
        self.amp_xy_cur += alpha * (self.amp_xy_tgt - self.amp_xy_cur)
        self.amp_z_cur  += alpha * (self.amp_z_tgt  - self.amp_z_cur)
        self.duty_cur   += alpha * (self.duty_tgt   - self.duty_cur)

        # avanzar fases con la frecuencia suavizada
        for i in range(4):
            self.phi[i] = (self.phi[i] + self.freq_cur*dt) % 1.0

        return [ (self.phi[i] + self.phase_offsets[i]) % 1.0 for i in range(4) ]

    def foot_position(self, phase, duty, stride_len=0.05, lift_height=0.02):
        """
        Devuelve (x, z) de la pata relativa a su posición 'neutra'
        phase: 0..1 -> posición en el ciclo
        duty: 0..1 -> % del ciclo en apoyo
        stride_len: avance total del pie (m)
        lift_height: altura máxima en swing (m)
        """
        if phase <= duty:
            # Apoyo: pie en el suelo, se mueve hacia atrás
            s = phase / duty  # 0..1
            x = (0.5 - s) * stride_len
            z = 0.0
        else:
            # Swing: pie en el aire, hacia delante
            s = (phase - duty) / (1 - duty)  # 0..1
            x = (-0.5 + s) * stride_len
            z = lift_height
        return x, z    
