import numpy as np
from scipy.ndimage import gaussian_filter
from stl import mesh

def generate_stl_from_scan(input_txt_path, output_stl_path, z_delta=0.2, center_distance=6.5, max_distance=20, interp_res=1, sigma=1.25):
    raw = np.loadtxt(input_txt_path)
    raw[raw < 0] = 0
    delimiters = np.where(raw == 9999)[0]

    slices = []
    start = 0
    for end in delimiters:
        slices.append(raw[start:end])
        start = end + 1

    if not slices:
        raise ValueError("No valid scan slices found.")

    r = np.array(slices)
    r = center_distance - r
    r[r > max_distance] = np.nan

    # Interpolate vertically (Z-axis resolution)
    if interp_res > 1:
        from scipy.interpolate import interp1d
        original_indices = np.arange(r.shape[0])
        interp_indices = np.linspace(0, r.shape[0] - 1, r.shape[0] * interp_res)
        r_interp = np.zeros((len(interp_indices), r.shape[1]))
        for col in range(r.shape[1]):
            f = interp1d(original_indices, r[:, col], kind='linear', fill_value="extrapolate")
            r_interp[:, col] = f(interp_indices)
        r = r_interp

    # Apply 2D Gaussian smoothing (like MATLAB's fspecial + filter2)
    r = gaussian_filter(r, sigma=sigma)

    rows, cols = r.shape
    theta = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    theta = np.tile(theta, (rows, 1))

    z = np.arange(0, rows * z_delta, z_delta)
    z = np.tile(z.reshape(-1, 1), (1, cols))

    x = r * np.cos(theta)
    y = r * np.sin(theta)

    # Fill NaNs with nearest valid value in same row
    for i in range(rows):
        valid = ~np.isnan(x[i])
        if valid.any():
            last_valid_x = x[i, valid][0]
            last_valid_y = y[i, valid][0]
            for j in range(cols):
                if np.isnan(x[i, j]):
                    x[i, j] = last_valid_x
                    y[i, j] = last_valid_y
                else:
                    last_valid_x = x[i, j]
                    last_valid_y = y[i, j]

    # Wrap around the last column to close the cylinder
    x = np.hstack([x, x[:, 0:1]])
    y = np.hstack([y, y[:, 0:1]])
    z = np.hstack([z, z[:, 0:1]])

    # Add top cap
    x_top = np.mean(x[-1])
    y_top = np.mean(y[-1])
    z_top = z[-1, 0] + z_delta
    x = np.vstack([x, np.full((1, x.shape[1]), x_top)])
    y = np.vstack([y, np.full((1, y.shape[1]), y_top)])
    z = np.vstack([z, np.full((1, z.shape[1]), z_top)])
    rows += 1

    # Create triangle faces
    faces = []
    for i in range(rows - 1):
        for j in range(cols):
            p0 = [x[i, j], y[i, j], z[i, j]]
            p1 = [x[i+1, j], y[i+1, j], z[i+1, j]]
            p2 = [x[i, j+1], y[i, j+1], z[i, j+1]]
            p3 = [x[i+1, j+1], y[i+1, j+1], z[i+1, j+1]]
            faces.append([p0, p1, p2])
            faces.append([p1, p3, p2])

    faces = np.array(faces)

    # Create STL mesh
    model = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        model.vectors[i] = f

    model.save(output_stl_path)
    return output_stl_path
