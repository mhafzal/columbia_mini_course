"""

A simple optimal savings problem.  The Bellman equation is

    v(x, z) = max_x' { u(R x + w z - x') + β E v(x', z')}

where  

    E v(x', z') = Σ_{z'} v(x', z') p(z, z')

We take 

    u(c) = c^{1 - γ} / (1 - γ)

and obtain p by discretizing

    log z' = ρ log z + d + σ η
    

"""

import numpy as np
import quantecon as qe
from numba import jit, prange


@jit(nopython=True)
def u(c, γ):
    return (c + 1e-10)**(1 - γ) / (1 - γ)


class SavingsProblem:

    def __init__(self, 
                 β=0.96,
                 γ=2.5,
                 ρ=0.9,
                 d=0.0,
                 σ=0.1,
                 r=0.05,
                 w=1.0,
                 z_grid_size=25,
                 x_grid_size=200,
                 x_grid_max=10):

        self.β, self.γ = β, γ
        self.R = 1 + r
        self.w = w
        self.z_grid_size, self.x_grid_size = z_grid_size, x_grid_size

        mc = qe.rouwenhorst(z_grid_size, d, σ, ρ)

        self.p = mc.P
        self.z_grid = np.exp(mc.state_values)
        self.x_grid = np.linspace(0.0, x_grid_max, x_grid_size)

    def pack_parameters(self):
        return self.β, self.γ, self.R, self.w, self.p, self.x_grid, self.z_grid

    def compute_fixed_point(self, 
                            tol=1e-4, 
                            max_iter=1000, 
                            verbose=True,
                            print_skip=25): 

        # Set initial condition
        v_in = np.ones((self.x_grid_size, self.z_grid_size))
        v_out = np.empty_like(v_in)

        # Set up loop
        params = self.pack_parameters()
        i = 0
        error = tol + 1

        while i < max_iter and error > tol:
            T(v_in, v_out, params)
            error = np.max(np.abs(v_in - v_out))
            i += 1
            if i % print_skip == 0:
                print(f"Error at iteration {i} is {error}.")
            v_in[:] = v_out

        if i == max_iter: 
            print("Failed to converge!")

        if verbose and i < max_iter:
            print(f"\nConverged in {i} iterations.")

        return v_out


@jit(nopython=True, parallel=True)
def T(v, v_out, params):

    n, m = v.shape
    β, γ, R, w, p, x_grid, z_grid = params

    for j in prange(m):
        z = z_grid[j]

        for i in range(n):
            x = x_grid[i]

            # Cash in hand at start of period
            y = R * x + w * z  
            # A variable to store largest recorded value
            max_so_far = - np.inf

            # Find largest x_grid index s.t. x' <= y
            idx = np.searchsorted(x_grid, y)

            # Step through x' with 0 <= x' <= y, find max
            for k in range(idx):
                x_next = x_grid[k]
                Ev = np.sum(v[k, :] * p[j, :])
                val = u(y - x_next, γ) + β * Ev
                max_so_far = max(val, max_so_far)

            v_out[i, j] = max_so_far


