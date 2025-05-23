import ants
import numpy as np
import pandas as pd
from scipy.special import i0e
# from skimage.metrics import structural_similarity


def logi0e(x):
    """
    Calculates the logarithm of the exponentially scaled modified Bessel function of the first kind (i0e) plus x.

    Parameters:
    x (float): The input value.

    Returns:
    float: The result of np.log(i0e(x)) + x.
    """

    return np.log(i0e(x)) + x

def rician_loglike(x, sigma, mu):
    """
    Calculate the log-likelihood of a Rician distribution.

    Parameters:
    x (float): The observed value.
    sigma (float): The scale parameter of the Rician distribution.
    mu (float): The location parameter of the Rician distribution.

    Returns:
    float: The log-likelihood of the Rician distribution.

    """
    return np.log(x) - 2*np.log(sigma) - (x**2 + mu**2)/(2*sigma**2) + logi0e(x*mu/sigma**2)

def make_sphere(img_shape, radius, center):
    """
    Create a binary sphere mask with the given radius and center.

    Parameters:
    img_shape (tuple): The shape of the output mask in the form (nx, ny, nz).
    radius (float): The radius of the sphere.
    center (tuple): The center coordinates of the sphere in the form (cx, cy, cz).

    Returns:
    numpy.ndarray: A binary mask representing the sphere.
    """

    nx, ny, nz = img_shape
    
    cx = nx - center[0] - nx//2
    cy = ny - center[1] - ny//2
    cz = nz - center[2] - nz//2
    
    X, Y, Z = np.meshgrid(np.arange(-ny//2, ny//2) + cy, np.arange(-nx//2, nx//2) + cx, np.arange(-nz//2, nz//2) + cz)
    D = np.sqrt(X**2 + Y**2 + Z**2)
    
    sphere = np.zeros(img_shape)
    sphere[D < radius] = 1

    return sphere

def make_circle(img_shape, radius, center):
    """
    Creates a binary circle image with the specified radius and center.

    Parameters:
    img_shape (tuple): The shape of the output image (height, width).
    radius (float): The radius of the circle.
    center (tuple): The center coordinates of the circle (x, y).

    Returns:
    numpy.ndarray: The binary circle image.
    """

    nx, ny = img_shape
    X, Y = np.meshgrid(np.arange(-nx//2, nx//2) + center[0], np.arange(-ny//2, ny//2) + center[1])
    D = np.sqrt(X**2 + Y**2)
    circle = np.zeros(img_shape)
    circle[D < radius] = 1
    return circle

def get_center(img):
    """
    Calculate the center coordinates of an image.

    Parameters:
        img (ants image): The input image.

    Returns:
        ndarray: The center coordinates of the image.
    """

    dir = np.diag(img.direction)
    nmid = np.array([x//2 for x in img.shape])
    spacing = np.array(img.spacing)

    return np.array(img.origin) + dir*nmid*spacing
     
def fit_ellipse_eig(x, y):
    """
    Fits an ellipse to a set of 2D points using the eigenvector approach.
    
    Parameters:
        x (array-like): The x-coordinates of the points.
        y (array-like): The y-coordinates of the points.
    
    Returns:
        array-like: The coefficients of the fitted ellipse.
    
    Note:
        Code generated by ChatGPT-4o
    """

    x = np.array(x)
    y = np.array(y)
    x = x[:, np.newaxis]
    y = y[:, np.newaxis]
    
    # Building the design matrix
    D = np.hstack((x * x, x * y, y * y, x, y, np.ones_like(x)))
    
    # Scatter matrix
    S = np.dot(D.T, D)
    
    # Constraint matrix
    C = np.zeros([6, 6])
    C[0, 2] = C[2, 0] = 2
    C[1, 1] = -1
    
    # Solving the generalized eigenvalue problem
    E, V = np.linalg.eig(np.dot(np.linalg.inv(S), C))
    n = np.argmax(np.abs(E))
    
    return V[:, n]

def fit_ellipse_svd(x, y):
    """
    Fits an ellipse to a set of 2D points using Singular Value Decomposition (SVD).

    Parameters:
    - x (array-like): x-coordinates of the points.
    - y (array-like): y-coordinates of the points.

    Returns:
    - array-like: The parameters of the fitted ellipse.

    The function takes in arrays of x and y coordinates and fits an ellipse to the points using SVD.
    It constructs a design matrix D and performs SVD on it to obtain the parameters of the ellipse.
    The function returns the parameters of the fitted ellipse.

    Note: The function assumes that the input points are in 2D and the number of points is greater than or equal to 6.
    """

    x = np.array(x)
    y = np.array(y)
    x = x[:, np.newaxis]
    y = y[:, np.newaxis]

    D = np.hstack((x * x, x * y, y * y, x, y, np.ones_like(x)))
    U, S, Vt = np.linalg.svd(D)

    return Vt[-1]

def gen_circle(center, r, axis, npoints=100):
    """
    Generate points on a circle in 3D space.

    Parameters:
        img (array-like): The input image.
        r (float): The radius of the circle.
        axis (str): The axis along which the circle lies ('x', 'y', or 'z').
        npoints (int, optional): The number of points to generate on the circle. Default is 100.

    Returns:
        pandas.DataFrame: A DataFrame containing the generated points on the circle.

    Note:
        The first point is the circle center point
    """

    t = np.linspace(0,1,npoints)

    if axis == 'x':
        x = np.ones_like(t) * center[0]
        y = r*np.cos(t*2*np.pi) + center[1]
        z = r*np.sin(t*2*np.pi) + center[2]

    elif axis == 'y':
        x = r*np.cos(t*2*np.pi) + center[0]
        y = np.ones_like(t) * center[1]
        z = r*np.sin(t*2*np.pi) + center[2]

    elif axis == 'z':
        x = r*np.sin(t*2*np.pi) + center[0]
        y = r*np.cos(t*2*np.pi) + center[1]
        z = np.ones_like(t) * center[2]

    points_df = pd.DataFrame.from_dict({'x':[center[0], *x], 'y':[center[1], *y], 'z':[center[2], *z]})

    return points_df

def transform_points(points_df, inv_transformlist):
    """
    Transforms a set of points using an inverse transformation list.

    Args:
        points_df (pandas.DataFrame): DataFrame containing the points to be transformed.
        inv_transformlist (list): List of inverse transformations to be applied to the points.

    Returns:
        tuple: A tuple containing two numpy arrays, p0 and p1. 
               p0 represents the original points, and p1 represents the transformed points.
    """
    
    points_xfm = ants.apply_transforms_to_points(3, points_df, transformlist=inv_transformlist)

    x0 = points_df['x'][1:] - points_df['x'][0]
    y0 = points_df['y'][1:] - points_df['y'][0]
    z0 = points_df['z'][1:] - points_df['z'][0]

    x1 = points_xfm['x'][1:] - points_xfm['x'][0]
    y1 = points_xfm['y'][1:] - points_xfm['y'][0]
    z1 = points_xfm['z'][1:] - points_xfm['z'][0]

    p0 = np.stack((x0,y0,z0))
    p1 = np.stack((x1,y1,z1))

    return p0, p1

def get_ellipse_params(x, y, method='svd'):
    """
    Calculates the parameters of an ellipse that best fits the given data points.

    Parameters:
        x (array-like): The x-coordinates of the data points.
        y (array-like): The y-coordinates of the data points.
        method (str): Fit method. svd or eig. Default: svd

    Returns:
        dict: A dictionary containing the ellipse parameters:
            - 'ABCDEF': The coefficients of the ellipse equation.
            - 'a': The semi-major axis length.
            - 'b': The semi-minor axis length.
            - 'x0': The x-coordinate of the ellipse center.
            - 'y0': The y-coordinate of the ellipse center.
            - 'theta': The rotation angle of the ellipse.
            - 'ecc': The eccentricity of the ellipse.
    """

    if method == 'svd':
        fit = fit_ellipse_svd(x, y)
    else:
        fit = fit_ellipse_eig(x,y)
    A,B,C,D,E,F = fit

    a,b = -np.sqrt( (2 * (A*E**2 + C*D**2 - B*D*E + (B**2 - 4*A*C)*F)*((A+C) + np.array([1,-1])*np.sqrt((A-C)**2+B**2)))) / (B**2 - 4*A*C) 
    x0 = (2*C*D - B*E)/(B**2-4*A*C)
    y0 = (2*A*E - B*D)/(B**2-4*A*C)
    theta = 0.5*np.arctan2(-B, C-A)
    ecc = np.sqrt(1 - b**2/a**2)

    return {'ABCDEF':fit, 'a':a, 'b':b, 'x0':x0, 'y0':y0, 'theta':theta, 'ecc':ecc}

def get_ellipse(a, b, theta, x0, y0, n=100, **kwargs):
    """
    Generate points on an ellipse.

    Parameters:
        - ellipse (dict): A dictionary containing the ellipse parameters.
            - 'a' (float): The semi-major axis length.
            - 'b' (float): The semi-minor axis length.
            - 'x0' (float): The x-coordinate of the center of the ellipse.
            - 'y0' (float): The y-coordinate of the center of the ellipse.
        - n (int): The number of points to generate on the ellipse. Default is 100.

    Returns:
        - x_el (ndarray): The x-coordinates of the points on the ellipse.
        - y_el (ndarray): The y-coordinates of the points on the ellipse.
    """
    
    t = np.linspace(0,1,n)*np.pi*2
    x_el = a * np.cos(t) * np.cos(theta) - b*np.sin(theta)*np.sin(t) + x0
    y_el = a * np.sin(theta) * np.cos(t) + b*np.cos(theta)*np.sin(t) + y0

    return x_el, y_el

def calc_psnr(img1, img2, mask):
    """
    Calculate the Peak Signal-to-Noise Ratio (PSNR) between two images.

    Parameters:
    img1 (ndarray or ants image): The first image.
    img2 (ndarray or ants image): The second image.
    mask (ndarray or ants image): The mask indicating the region of interest.

    Returns:
    float: The PSNR value.

    """
    I1 = img1[mask==1]
    I2 = img2[mask==1]
    MSE = np.sum((I1-I2)**2)/len(I1)
    R = np.mean([max(I1),max(I2)])
    PSNR = 10*np.log10(R**2/MSE)
    return MSE, PSNR

# def calc_ssim(img1, img2, mask, kw=11, sigma=0):
#     gauss_window = False
#     use_sample_covariance = True
#     if sigma:
#         gauss_window = True
#         use_sample_covariance = False

#     mssim, S = structural_similarity(
#         img1, img2, win_size=kw, data_range=1, gradient=False,
#         multichannel=False, gaussian_weights=gauss_window, full=True, use_sample_covariance=use_sample_covariance,
#         sigma=sigma)
    
#     return S[mask==1].mean()

def calc_snr_diff(img1, img2, mask):
    img_diff = img1-img2
    img_mean = (img1+img2)/2
    return img_mean[mask==1].mean()/img_diff[mask==1].std()/np.sqrt(2)

