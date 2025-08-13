import math

class CPG:
    def __init__(self, gait="walk"):
        self.phi = [0.0, 0.25, 0.5, 0.75]  # FR, FL, RR, RL (ajustaremos orden si el tuyo es otro)
        self.freq = 0.8  # Hz inicial (velocidad de paso)
        self.amp_xy = 1.0
        self.amp_z = 1.0
        self.set_gait(gait)

    def set_gait(self, gait):
        # Solo “walk” 4 tiempos por ahora (duty alto). Más adelante: trot, pace, etc.
        self.phase_offsets = [0.0, 0.25, 0.5, 0.75]
        self.duty = 0.65  # % del ciclo en apoyo (ajustable)
        self.gait = gait

    def set_velocity(self, vx, vy, wz):
        # Mapea velocidad a frecuencia y amplitud de forma muy conservadora
        speed = math.hypot(vx, vy) + abs(wz)*0.3
        self.freq = max(0.2, min(2.0, 0.6 + 1.4*speed))  # Hz
        self.amp_xy = min(1.5, 0.6 + 1.2*speed)
        self.amp_z  = min(1.2, 0.5 + 0.7*speed)

    def update(self, dt):
        if dt <= 0: return self.phi
        # avanza fases y envuélvelas [0,1)
        for i in range(4):
            self.phi[i] = (self.phi[i] + self.freq*dt) % 1.0
        # devuelve fases “desfasadas” por pata
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
