# DSP and Realtime Safety Policy

PAP Forge should only graduate into true plugin compilation with the following policy enforced:

- No heap allocation in the audio thread.
- No blocking I/O in realtime callbacks.
- Parameter changes must be lock-safe or lock-free.
- Oversampling or FIR rebuilds must happen outside the audio thread.
- Generated DSP modules must declare CPU class and memory behavior.
- Default builds must clip safely or expose explicit gain staging.
