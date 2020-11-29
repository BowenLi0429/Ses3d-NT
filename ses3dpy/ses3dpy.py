#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SES3dPy
-------

This module is ought to handle Ses3d-NT simulations using Python. The focus of
Ses3dPy is primarily directed on handling data generated by Ses3d. It is the
aim of Ses3dPy to make Ses3ds data handling and processing more easy and
fitting to one’s individual needs. Included procedures may adress model
parameters, velocity fields and sensitivity kernels.
Throughout Ses3dPy, as in Ses3d, θ-components (colatitude) are labelled with x,
φ-components (longitude) with y and r-components with z. For further
information have a look at the Ses3d manual.

Usage
=====

>>> import Ses3dPy
>>> config = read_config_file( [file_name] )
>>> field = Sed3dPy.read_field( config, [file_name] )
>>> ...

Caution
-------
Keep in mind that Ses3d-NT may produce huge amounts of data. As an example, a
3d velocity field associated with its point coordinates of a relatively small
model with 200×200×100 collocation points takes around 100 MBs of main-memory
by an accuracy of double precision. To process data of realistic simulations,
it can easily consume several gigabytes of main memory.

Dependencies
------------
The following software requirements should be fulfilled: Python ≥ 2.6, numpy ≥
1.1.0, matplotlib ≥ 1.0.0, vtk ≥ 5.0.4 and obspy.core ≥ 3.6. For high quality
visualisation results it is useful to have LaTeX and AMSLaTeX installed which
enables Matplotlib to render text much nicer.

:copyright:
    Stefan Mauerberger <mauerberger@geophysik.uni-muenchen.de>, 2013

:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html) """


__version__ = '0.5.beta -- Sat Mar  2 09:11:52 CET 2013'


def read_config_file(file):
    """
This function reads in a Ses3d-NT configuration file. The parameter set will 
be returned as an associated dictionary. 
Parameter values having a capital X in its name are lists with three
entries. The X represents the spatial directions. In lists appearing, the
zero entry corresponds to the x-, the first to the y- and the second to the
z-direction.

Parameters:
-----------
par_file : string
     configuration filename """

    from namelist import namelist2dict

    config = namelist2dict(file)

    pars = {}
    pars['nX_global'] = (config['grid'][0]['nx'], config['grid'][0]['ny'],
        config['grid'][0]['nz'])
    pars['lpd'] = config['grid'][0]['lpd']
    pars['minX'] = (90.0 - config['model'][0]['lat_max'],
        config['model'][0]['lon_min'], config['model'][0]['rad_min'])
    pars['maxX'] = (90.0 - config['model'][0]['lat_min'],
        config['model'][0]['lon_max'], config['model'][0]['rad_max'])
    pars['pml'] = config['grid'][0]['pml']

    if "mu" in config['model'][0]:
        pars['mu'] = config['model'][0]['mu']
    if "lambda" in config['model'][0]:
        pars['lambda'] = config['model'][0]['lambda']
    if "rhoinv" in config['model'][0]:
        pars['rhoinv'] = config['model'][0]['rhoinv']

    return pars

def raw_empty_field(par):
    """
Returns an empty field 

Parameters:
-----------
par: dictionary 
    Dictionary with parameters from read_par_file() """

    from numpy import empty

    lpd = par['lpd'] + 1
    shape = list(par['nX_global']) + [lpd, lpd, lpd]
    return empty(shape)
    


def read_field(par, file_name):
    """
    This function reads Ses3ds raw binary files, e.g. 3d velocity field
    snapshots, as well as model parameter files or sensitivity kernels. It
    returns the field as an array of rank 3 with shape (nx*lpd+1, ny*lpd+1,
    nz*lpd+1), discarding the duplicates by default.

    Parameters:
    -----------
    par: dictionary
        Dictionary with parameters from read_par_file()
    file_name: str
        Filename of Ses3d 3d raw-output
    """
    lpd = par['lpd'] + 1
    shape = list(par['nX_global']) + [lpd, lpd, lpd]

    field = read_raw_output(file_name, shape)

    return pack_6to3(field)


def write_field(config, field, file_name):
    """
    XXX: Missing doc
    """
    field = unpack_3to6(field[:, :, :], config['lpd'])
    write_raw_output(file_name, field)


def pop_duplicates(config, field):
    """
    XXX: Missing doc
    """
    from numpy import ones
    # delete duplicates at the element borders
    lpd = config['lpd']
    shp_fin = [nX * lpd for nX in config['nX_global']]
    for a, i in enumerate(shp_fin):
        mask = ones(i, dtype='bool')
        mask[::lpd] = False
        field = field.compress(mask, axis=a)

    return field


def get_knots(lpd):
    """
    Returns the sampling points connected to the n-th lagrange polynomial.

    Parameters:
    -----------
    lpd : int
        Lagrange polynomial degree (between 2 to 7)
    """
    from numpy import array

    if lpd == 2:
        knots = array([-1.0, 0.0, 1.0])
    elif lpd == 3:
        knots = array([-1.0, -0.4472135954999579, 0.4472135954999579, 1.0])
    elif lpd == 4:
        knots = array([-1.0, -0.6546536707079772, 0.0, 0.6546536707079772,
            1.0])
    elif lpd == 5:
        knots = array([-1.0, -0.7650553239294647, -0.2852315164806451,
            0.2852315164806451, 0.7650553239294647, 1.0])
    elif lpd == 6:
        knots = array([-1.0, -0.8302238962785670, -0.4688487934707142, 0.0,
            0.4688487934707142, 0.8302238962785670, 1.0])
    elif lpd == 7:
        knots = array([-1.0, -0.8717401485096066, -0.5917001814331423,
            -0.2092992179024789, 0.2092992179024789, 0.5917001814331423,
            0.8717401485096066, 1.0])
    return knots


def generate_coordinates(par, pcolor=False, no_dup=True):
    """
    This function calculates the coordinates of a Ses3d simulation based on its
    parameters. A list containing three vectors, spanning the model, is
    returned. By default the vectors do not contain duplicates. The first
    vector in the list corresponds to the θ-direction and has (nx
    global+px)*(lpd-1) entries, the second to the φ-direction with (ny
    global+py)*(lpd-1) entries and the third to r-direction with (nz
    global+pz)*(lpd-1) entries. Setting the keyarg pcolor=True returns n+1
    entries in every direction which is convenient for many plotting functions.

    Parameters:
    -----------
    par : dictionary
        containing the parameters of a simulation ( see: read_par_file() )
    pcolor : bool
        if True n+1 instead of n coordinate values are generated
        this is needed by some plotting commands (e.g. it is useful for pcolor)
        default is False
    no_dup : bool
        by default duplicates are suppressed (take care pcolorfast can not deal
        with duplicates)
    """
    from numpy import asarray, empty, append, linspace, ones

    nX_global = asarray(par['nX_global'])
    lpd = par['lpd']
    maxX = asarray(par['maxX'])
    minX = asarray(par['minX'])

    knots = get_knots(lpd)
    knots = (knots + 1) * 0.5

    theta = empty((0,), dtype='float32')
    phi = empty((0,), dtype='float32')
    r = empty((0,), dtype='float32')

    lpd = lpd + 1

    delta = (maxX - minX) / nX_global.astype('float')

    maxX = maxX - delta

    for i in linspace(minX[0], maxX[0], nX_global[0]):
        theta = append(theta, i + delta[0] * knots)
    mask = ones(nX_global[0] * lpd, dtype='bool')
    if no_dup:
        mask[::lpd] = False
    if pcolor:
        mask[0] = True
    theta = theta[mask]

    for i in linspace(minX[1], maxX[1], nX_global[1]):
        phi = append(phi, i + delta[1] * knots)
    mask = ones(nX_global[1] * lpd, dtype='bool')
    if no_dup:
        mask[::lpd] = False
    if pcolor:
        mask[0] = True
    phi = phi[mask]

    for i in linspace(minX[2], maxX[2], nX_global[2]):
        r = append(r, i + delta[2] * knots)
    mask = ones(nX_global[2] * lpd, dtype='bool')
    if no_dup:
        mask[::lpd] = False
    if pcolor:
        mask[0] = True
    r = r[mask]

    return theta, phi, r


def mesh3d(x, y, z):
    """
    This function generates a 3-dimensional coordinate grid. For vectors x, y
    and z with lengths Nx, Ny and Nz, three (Nx, Ny, Nz) shaped arrays X, Y and
    Z are returned. These arrays are filled with the elements of x, y and z
    repeatedly. This function can be used to associate indexed fields with its
    coordinate values, especially by transforming them from curvilinear
    coordinates. Let a be an indexed field and let the vectors x, y, z span the
    model. Then the coordinates for the point a[i,j,k] are given by X[i,j,k],
    Y[i,j,k] and Z[i,j,k].

    Parameters:
    -----------
    x,y,z : list
         Coordinates spaning the model
    """
    from numpy import asarray

    x = asarray(x).astype('float32')
    y = asarray(y).astype('float32')
    z = asarray(z).astype('float32')

    numX, numY, numZ = x.size, y.size, z.size

    X = x.reshape(numX, 1, 1)
    X = X.repeat(numY, axis=1)
    X = X.repeat(numZ, axis=2)

    Y = y.reshape(1, numY, 1)
    Y = Y.repeat(numX, axis=0)
    Y = Y.repeat(numZ, axis=2)

    Z = z.reshape(1, 1, numZ)
    Z = Z.repeat(numX, axis=0)
    Z = Z.repeat(numY, axis=1)

    return X, Y, Z


def write_vtk(coord, values, file):
    """
    This function converts Ses3ds data to the VTK file format. It writes a VTK
    binary file containing the fields specified in the dictionary fields.
    Coordinate points must be Cartesian and given as a list coord=(X, Y, Z). In
    the dictionary fields, the keys and values correspond to the field-name and
    the field itself. Whereas the field has to be a list of its arrays.
    For instance fields={’Velocity’:[vx, vy, vz], ’Rho’:[rho,] } writes the
    veloc ity vector v = (vθ , vφ , vr ) and the density ρ into the VTK file.
    By all means all arrays have to have the exact same shape and order.

    Parameters:
    -----------
    coord : list [ X, Y, Z ]
        Cartesian coordinates associated with the fields
        (to generate coordinates use generate_coordinates() and mesh3d() )
    values : dict { 'name':[ values, ] }
        fields in x, y, z direction from read_field()
    file : str
        file name of the output file
    """
    from numpy import asarray
    from vtk import vtkStructuredGrid, vtkPoints, vtkStructuredGridWriter, \
        vtkDataArray

    # vtkDataTypes: 8 = int32; 10 = float32

    # transform points to linear byte stream
    coord = asarray(coord)
    shp = coord.shape
    coord = coord.T.flatten()
    # generate vtk array carrying points
    points_arr = vtkDataArray.CreateDataArray(10)
    points_arr.SetNumberOfComponents(shp[0])
    points_arr.SetVoidArray(coord.ravel(), coord.size, 10)
    # vtk points object
    points = vtkPoints()
    points.SetData(points_arr)
    # generate a vtk structured grid and set points
    sgrid = vtkStructuredGrid()
    sgrid.SetDimensions((shp[1], shp[2], shp[3]))
    sgrid.SetPoints(points)

    # generate vtk-arrays of the submitted fields
    arrays = {}
    for name, value in values.iteritems():
        value = asarray(value).astype('float32')
        shp = value.shape
        # transform fields to linear byte stream (as well as points are)
        values[name] = value.T.flatten()
        # generate array and set values
        arrays[name] = vtkDataArray.CreateDataArray(10)
        arrays[name].SetNumberOfComponents(shp[0])
        arrays[name].SetName(name)
        arrays[name].SetVoidArray(values[name].ravel(), values[name].size, 10)

    # associate points with fields
    for array in arrays.itervalues():
        sgrid.GetPointData().AddArray(array)

    # write vtk file
    writer = vtkStructuredGridWriter()
    writer.SetInput(sgrid)
    writer.SetFileTypeToBinary()
    writer.SetFileName(file)

    return writer.Write()


def pack_6to3(field):
    """
    XXX: Missing doc
    """
    from numpy import rollaxis, asarray
    field = asarray(field[:, :, :, :, :, :])
    # Make new shape
    shp_r6 = field.shape
    shp_r3 = [n * l for n, l in zip(shp_r6[:3], shp_r6[3:])]
    # reorder: [x,y,z,lpd+1,lpd+1,lpd+1] to v[x,lpd+1,y,lpd+1,z,lpd+1]
    field = rollaxis(rollaxis(field, 3, 1), 3, 5)
    # reshape: v[nx,lpd,ny,lpd,nz,lpd] to v[nx*(lpd+1),ny*(lpd+1),nz*(lpd+1)]
    field = field.reshape(shp_r3)
    # z-coordinates are upside down
    return field[:, :, :]


def unpack_3to6(r3, lpd):
    """
    Missing doc
    """
    from numpy import asarray, empty
    r3 = asarray(r3[:, :, :])
    lpd = lpd + 1
    nx, ny, nz = r3.shape / asarray([lpd, lpd, lpd])
    r6 = empty([nx, ny, nz, lpd, lpd, lpd])

    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                for il in range(lpd):
                    for jl in range(lpd):
                        for kl in range(lpd):

                            # Coordinate transformation
                            i3 = i * lpd + il
                            j3 = j * lpd + jl
                            k3 = k * lpd + kl

                            # Store values in new field
                            r6[i, j, k, il, jl, kl] = r3[i3, j3, k3]

    return r6[:, :, :, :, :, :]


def write_raw_output(file_name, field, dtype='float32'):
    """
    Missing doc
    """
    from numpy import asarray
    field = asarray(field[:, :, :, :, :, :], dtype=dtype)
    field = field.T
    field = field.flatten()
    with open(file_name, 'w') as fh:
        fh.write(field)
    fh.close()


def read_raw_output(file_name, shape):
    """
    Missing doc
    """
    from numpy import ndarray
    field = ndarray(shape, buffer=open(file_name, 'r').read(), dtype="float32",
        order='F')
    return field