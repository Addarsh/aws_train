"""
image_utils is has helpul functions to process an image.
"""
import cv2
import numpy as np
import math
import csv
import json
import random
import colour
import colormath
import re
import matplotlib.pyplot as plt

from scipy.sparse import diags
from scipy.optimize import minimize
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
from colormath import color_diff_matrix
from .common import MaskDirection, SkinTone
from PIL import Image


class ImageUtils:
    windowName = ""

    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    """
    Initialize conditions for plottig.
    """

    @staticmethod
    def init():
        ImageUtils.windowName = "image"
        cv2.namedWindow(ImageUtils.windowName, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(ImageUtils.windowName, 900, 900)

    """
    Reads srgb image from given image path.
    """

    @staticmethod
    def read_rgb_image(image_path):
        return cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)

    """
    Reads a gray scale image from given path.
    """
    @staticmethod
    def read_grayscale_image(image_path):
        return cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2GRAY)

    """
    Converts given gray scale image to boolean mask [value >=150 -> 1 else 0].
    """
    @staticmethod
    def get_boolean_mask(grayscale_image):
        return (grayscale_image >= 150).astype(np.bool)

    """
    Reads and returns a LAB scale and gray scale image from given image path.
    """

    @staticmethod
    def read(imagePath):
        img = cv2.imread(imagePath)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        return gray, lab, img, hsv

    """
    ResizeWithAspectRatio resizes given image maintaining aspect ratio.
    """

    @staticmethod
    def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
        dim = None
        (h, w) = image.shape[:2]

        if width is None and height is None:
            return image
        if width is None:
            r = height / float(h)
            dim = (int(w * r), height)
        else:
            r = width / float(w)
            dim = (width, int(h * r))

        return cv2.resize(image, dim, interpolation=inter)

    """
    Performs histogram equalization to adjust contrast in gray image.
    """

    @staticmethod
    def equalize_hist(gray):
        return cv2.equalizeHist(gray)

    """
    Performs adaptive equalization to adjust contrast in gray image. Currently, not using this function but could be 
    used in the future.
    """

    @staticmethod
    def adaptive_hist(gray):
        clahe = cv2.createCLAHE(clipLimit=0.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    """
    plot_points plots given points on given gray image.
    """

    @staticmethod
    def plot_points(img, points):
        for (x, y) in points:
            cv2.circle(img, (x, y), 0, 255, 0)

    """
    plot_points plots given points on given RGB image.
    """

    @staticmethod
    def plot_points_new(img, points, radius=2, color=[255, 0, 0]):
        for p in points:
            y, x = int(p[0]), int(p[1])
            cv2.circle(img, (x, y), radius, color, -1)
        return img

    """
    Returns copy of image with given points plotted in given color as well as the given mask colored green.
    """

    def plot_points_and_mask(img, points, mask, radius=5, color=[255, 0, 0]):
        clone = img.copy()
        clone[mask] = np.array([0, 255, 0])
        clone = ImageUtils.plot_points_new(clone, points, radius=radius, color=color)
        return clone

    """
    plot_arrowed_line plots arrowed lines between given set of points on given RGB image.
    """

    @staticmethod
    def plot_arrowed_line(img, points, radius=2, color=[0, 0, 255]):
        for i in range(1, len(points)):
            ys, xs = int(points[i - 1][0]), int(points[i - 1][1])
            ye, xe = int(points[i][0]), int(points[i][1])
            cv2.arrowedLine(img, (xs, ys), (xe, ye), color, 2, tipLength=0.5)

    """
    Plots a rectangle with p1 as left-top point and p2 as right-botton point.
    """

    @staticmethod
    def plot_rect(img, p1, p2):
        cv2.rectangle(img, p1, p2, 0, 2)

    """
    Plots a histogram of the given image for given mask.
    """

    def plot_histogram(img, mask, channel=0, block=True, bins=40, fig_num=1, xlim=[0, 256]):
        plt.figure(fig_num)
        plt.hist(img[mask][:, channel], bins=bins, density=False, histtype="step")
        plt.xlim(xlim)
        plt.show(block=block)

    """
    plot_gray_histogram plots histogram of the given gray image for given mask.
    """

    def plot_gray_histogram(gray, mask, block=True, bins=255):
        plt.hist(gray[mask], bins=bins, density=True)
        plt.xlim([0, 256])
        plt.show(block=block)

    """
    Shows grid of skin tone colors stacked vertically on top of each.
    """

    @staticmethod
    def show_skin_tone_color_grid(skin_tones):

        grid_height = 800
        img_list = []
        for sk in skin_tones:
            img_height = round(sk.percent_of_face_mask*0.01*grid_height)
            img = np.full((img_height, 200, 3), 0, np.uint8)
            img_list.append(img)

        for i, img in enumerate(img_list):
            color = skin_tones[i].rgb
            img[:, :, :] = np.flip(color)

        cv2.imshow('color_grid', np.vstack(img_list))
        cv2.waitKey(0)

    """
    Saves grid of skin tone colors stacked vertically on top of each as a png image.
    """

    @staticmethod
    def save_skin_tones_to_file(image_name, skin_tones, icc_profile_path="",skip_text=False):

        grid_height = 800
        img_list = []
        for sk in skin_tones:
            img_height = round(sk.percent_of_face_mask * 0.01 * grid_height)
            img = np.full((img_height, 200, 3), 0, np.uint8)
            img_list.append(img)

        for i, img in enumerate(img_list):
            color = skin_tones[i].rgb
            percent_of_face_mask = round(skin_tones[i].percent_of_face_mask)
            img[:, :, :] = color

            hsv = skin_tones[i].hsv
            h = round(hsv[0])
            s = round(hsv[1])
            v = round(hsv[2])
            sl = round(skin_tones[i].hls[2])

            if not skip_text:
                # Add text to image.
                hsvStr = "H: " + str(h) + ",S: " + str(sl) + ",S:" + str(s) + ",V: " + str(v) + ",P:" + str(
                    percent_of_face_mask)
                img[:, :, :] = cv2.putText(img, hsvStr, (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (210, 0, 0), 1,
                                           cv2.LINE_AA)

        save_img = np.vstack(img_list)
        ImageUtils.save_image_to_file(save_img, image_name, icc_profile_path)

    @staticmethod
    def save_image_to_file(rgb_array, image_name, icc_profile_path=""):
        im = Image.fromarray(rgb_array)
        if icc_profile_path != "":
            with open(icc_profile_path, "rb") as f:
                icc = f.read()
            im.save(image_name, icc_profile=icc)
        else:
            im.save(image_name)

    """
    color return the RGB tuple of given hex color. Hex color format is #FF0033.
    """

    @staticmethod
    def color(hexcolor):
        h = hexcolor.lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    """
    HEX2RGB returns RGB numpy array for given hex color.
    """

    def HEX2RGB(hexcolor):
        h = hexcolor.lstrip('#')
        return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])

    """
    rgb_to_hex converts given RGB tuple to a hex string.
    """

    @staticmethod
    def rgb_to_hex(p):
        return '#{:02x}{:02x}{:02x}'.format(p[0], p[1], p[2])

    """
    set_color sets given points to given color.
    """

    @staticmethod
    def set_color(img, pts, clr, radius=0):
        for _, p in enumerate(pts):
            cv2.circle(img, p, 0, clr, radius)

    """
    avg_color returns the average color of the given points. The points
    and image are in RGB color space.
    """

    @staticmethod
    def avg_color(img, pts):
        if len(pts) == 0:
            return None
        c = (0, 0, 0)
        for _, p in enumerate(pts):
            nc = img[p[0], p[1]]
            c = (c[0] + nc[0] ** 2, c[1] + nc[1] ** 2, c[2] + nc[2] ** 2)

        l = len(pts)
        # return ImageUtils.brighter((int(c[0]/l),int(c[1]/l),int(c[2]/l)))
        return (int(math.sqrt(c[0] / l)), int(math.sqrt(c[1] / l)), int(math.sqrt(c[2] / l)))

    """
    avg_lab_color is the average color of the given points. The points and
    image are in LAB color space.
    """

    def avg_lab_color(img, pts):
        if len(pts) == 0:
            return None
        c = [0, 0, 0]
        l = len(pts)
        for p in pts:
            nc = img[p[0], p[1]]
            c = [sum(x) for x in zip(c, nc)]

        return (int(c[0] / l), int(c[1] / l), int(c[1] / l))

    """
    average intensity returns the average intensity of the given set of points.
    Input img must be dimension 1.
    """

    @staticmethod
    def avg_intensity(img, pts):
        avg = 0.0
        for p in pts:
            x, y = p
            avg += img[x, y]
        return avg / len(pts)

    """
    additiveBlendChannel will blend given RGB color channels additively.
    """

    @staticmethod
    def additiveBlendChannel(a, b, t):
        return int(math.sqrt(t * a * a + (1 - t) * b * b))

    """
    additiveBlendRGB will additively blend the given RGB colors with the given
    ratio alpha:1-alpha in that order.
    """

    @staticmethod
    def additiveBlendRGB(c1, c2, alpha):
        r = ImageUtils.additiveBlendRGB(c1[0], c2[0], alpha)
        g = ImageUtils.additiveBlendRGB(c1[1], c2[1], alpha)
        b = ImageUtils.additiveBlendRGB(c1[2], c2[2], alpha)
        return (r, g, b)

    """
    Convert from RGB color to CYMK space.
    """

    @staticmethod
    def rgb_to_cmyk(r, g, b):
        rgb_scale = 255
        cmyk_scale = 100

        if (r == 0) and (g == 0) and (b == 0):
            # black
            return 0, 0, 0, cmyk_scale

        # rgb [0,255] -> cmy [0,1]
        c = 1 - r / float(rgb_scale)
        m = 1 - g / float(rgb_scale)
        y = 1 - b / float(rgb_scale)

        # extract out k [0,1]
        min_cmy = min(c, m, y)
        c = (c - min_cmy)
        m = (m - min_cmy)
        y = (y - min_cmy)
        k = min_cmy

        # rescale to the range [0,cmyk_scale]
        return c * cmyk_scale, m * cmyk_scale, y * cmyk_scale, k * cmyk_scale

    """
    Convert from CMYK color to RGB space.
    """

    @staticmethod
    def cmyk_to_rgb(c, m, y, k):
        rgb_scale = 255
        cmyk_scale = 100

        r = rgb_scale * (1.0 - (c + k) / float(cmyk_scale))
        g = rgb_scale * (1.0 - (m + k) / float(cmyk_scale))
        b = rgb_scale * (1.0 - (y + k) / float(cmyk_scale))
        return (r, g, b)

    """
    subtractiveBlendRGB blends given list of color subtractively.
    """

    @staticmethod
    def subtractiveBlendRGB(list_of_colours):
        """
        input: list of rgb, opacity (r,g,b,o) colours to be added, o acts as weights.
        output (r,g,b)
        """
        C = 0
        M = 0
        Y = 0
        K = 0

        for (r, g, b, o) in list_of_colours:
            c, m, y, k = ImageUtils.rgb_to_cmyk(r, g, b)
            C += o * c
            M += o * m
            Y += o * y
            K += o * k

        return ImageUtils.cmyk_to_rgb(C, M, Y, K)

    """
    brighter makes the color by multiplying by constant.
    """

    def brighter(color):
        r, g, b = color
        c = min(1.25, 255 / max(r, b, b))
        return (int(r * c), int(g * c), int(b * c))

    """
    filter_by_color returns all points of the image that belong to given
    color.
    """

    def filter_by_color(img, clr):
        points = []
        for i in range(img.shape[1]):
            for j in range(img.shape[0]):
                if not np.array_equal(img[j][i], clr):
                    continue
                points.append((i, j))
        return points

    """
    rspectrum_lhtss calculates the reflectance spectrum for the
    given RGB color using the Least Hyperbolic Tangent Slope Squared (LHTSS)
    specified by Scott Burns on his site: http://scottburns.us/reflectance-curves-from-srgb/.
    This is the Python version of the specified MATLAB code.
    The reflectance spans the wavelength range 380-730 nm in 10 nm increments.
    rgb is a 3 element tuple of color in 0-255 range.
    rho is a (36,1) numpy array of reconstructed reflectance values, all (0->1).
    """

    def rspectrum_lhtss(rgb):
        T = ImageUtils.read_T_matrix()

        # convert from rgb tuple to list.
        rgb = [rgb[0], rgb[1], rgb[2]]

        numIntervals = T.shape[1]
        rho = np.zeros(numIntervals)

        # Black input color.
        if rgb == (0, 0, 0):
            rho = 0.0001 * np.ones(numIntervals)
            return rho

        # White input color.
        if rgb == (255, 255, 255):
            rho = np.ones(numIntervals)
            return rho

        # 36 by 36 Jacobian having 4 main diagonal
        # and -2 on off diagonals, except for first and
        # last main diagonal are 2.
        D = diags([-2, 4, -2], [-1, 0, 1], shape=(numIntervals, numIntervals)).toarray()
        D[0][0] = 2
        D[numIntervals - 1, numIntervals - 1] = 2

        # Scale RGB values to between 0-1 and remove
        # gamma correction.
        for i in range(3):
            rgb[i] = rgb[i] / 255.0
            if rgb[i] < 0.04045:
                rgb[i] = rgb[i] / 12.92
            else:
                rgb[i] = math.pow((rgb[i] + 0.055) / 1.055, 2.4)

        # Initialize paramters in optimization.
        z = np.zeros(numIntervals)
        lamda = np.zeros(3)
        ftol = math.pow(10, -8)
        count = 0
        NUM_ITERS = 100

        # Newton's method iteration.
        divider = 2
        while count <= NUM_ITERS:
            d0 = (np.tanh(z) + 1) / divider
            d1 = np.diag(np.power(1 / np.cosh(z), 2) / divider)
            d2 = np.diag(-np.power(1 / np.cosh(z), 2) * np.tanh(z) * (2 / divider))
            F = np.concatenate(
                (np.matmul(D, z) + np.matmul(d1, np.matmul(np.transpose(T), lamda)), np.matmul(T, d0) - rgb))
            J1 = np.concatenate(
                (D + np.diag(np.matmul(d2, np.matmul(np.transpose(T), lamda))), np.matmul(d1, np.transpose(T))), axis=1)
            J2 = np.concatenate((np.matmul(T, d1), np.zeros((3, 3))), axis=1)
            J = np.concatenate((J1, J2), axis=0)
            delta = np.matmul(np.linalg.inv(J), -F)
            z = z + delta[:numIntervals]
            lamda = lamda + delta[numIntervals:]
            if np.all(np.less(np.absolute(F) - ftol, np.zeros(numIntervals + 3))):
                # Found solution.
                rho = (np.tanh(z) + 1) / divider
                return rho
            count += 1

        raise Exception("rspectrum_lhtss: No solution found in iteration")

    """
    rspectrum_lhtss calculates the reflectance spectrum for the
    given RGB color using the Iterative Least Slope Squared (LHTSS)
    specified by Scott Burns on his site: http://scottburns.us/reflectance-curves-from-srgb/.
    This is the Python version of the specified MATLAB code.
    The reflectance spans the wavelength range 380-730 nm in 10 nm increments.
    rgb is a 3 element tuple of color in 0-255 range.
    rho is a (36,1) numpy array of reconstructed reflectance values, all (0->1).
    """

    def rspectrum_ilss(rgb):
        T = np.power(ImageUtils.read_T_matrix(), 1)

        # convert from rgb tuple to list.
        rgb = np.array([rgb[0], rgb[1], rgb[2]], dtype=np.float)

        numIntervals = T.shape[1]
        rho = np.ones(numIntervals) / 2.0
        rhomin = 0.00001
        rhomax = 1

        if np.array_equal(rgb, [0, 0, 0]):
            return rhomin * np.ones(numIntervals)

        if np.array_equal(rgb, [1, 1, 1]):
            return rhomax * np.ones(numIntervals)

        # Scale RGB values to between 0-1 and remove
        # gamma correction.
        for i in range(3):
            rgb[i] = rgb[i] / 255.0
            if rgb[i] < 0.04045:
                rgb[i] = rgb[i] / 12.92
            else:
                rgb[i] = math.pow((rgb[i] + 0.055) / 1.055, 2.4)

        # 36 by 36 Jacobian having 4 main diagonal
        # and -2 on off diagonals, except for first and
        # last main diagonal are 2.
        # D = diags([-2, 4, -2], [-1, 0, 1], shape=(numIntervals, numIntervals)).toarray()
        D = diags([-6, 20, -6], [-1, 0, 1], shape=(numIntervals, numIntervals)).toarray()
        D[0][0] = 2
        D[numIntervals - 1, numIntervals - 1] = 2

        B = np.linalg.inv(np.concatenate(
            (np.concatenate((D, np.transpose(T)), axis=1), np.concatenate((T, np.zeros((3, 3))), axis=1)), axis=0))

        R = np.matmul(B[:numIntervals, numIntervals:], rgb)

        NUM_ITERS = 10
        count = 0
        while count == 0 or (count <= NUM_ITERS and (np.any(np.less(rho - rhomin, np.zeros(numIntervals))) or np.any(
                np.less(rhomax - rho, np.zeros(numIntervals))))):
            # Create K1 for fixed reflectance at rhomax.
            fixed_upper_logical = rho >= rhomax
            fixed_upper = np.nonzero(fixed_upper_logical)[0]
            num_upper = len(fixed_upper)
            K1 = np.zeros((num_upper, numIntervals))
            K1[range(K1.shape[0]), fixed_upper] = 1

            # Create K0 for fixed reflectance at rhomin.
            fixed_lower_logical = rho <= rhomin
            fixed_lower = np.nonzero(fixed_lower_logical)[0]
            num_lower = len(fixed_lower)
            K0 = np.zeros((num_lower, numIntervals))
            K0[range(K0.shape[0]), fixed_lower] = 1

            # Set up linear system.
            K = np.concatenate((K1, K0), axis=0)
            C = np.matmul(np.matmul(B[:numIntervals, :numIntervals], np.transpose(K)),
                          np.linalg.inv(np.matmul(K, np.matmul(B[:numIntervals, :numIntervals], np.transpose(K)))))
            rho = R - np.matmul(C, np.matmul(K, R) - np.concatenate(
                (rhomax * np.ones(num_upper), rhomin * np.ones(num_lower)), axis=0))
            rho[fixed_upper_logical] = rhomax
            rho[fixed_lower_logical] = rhomin

            count += 1

        if count > NUM_ITERS:
            raise Exception("No solution found after: ", str(NUM_ITERS), " iterations")

        return rho

    """
    rspectrum_foundation estimates the reflectance of a given foundation color.
    """

    def rspectrum_foundation(rgb):
        T = ImageUtils.read_T_matrix()

        # convert from rgb tuple to list.
        rgb = np.array([rgb[0], rgb[1], rgb[2]], dtype=np.float)
        numIntervals = T.shape[1]
        rhomin = 0.0001
        rhomax = 1.0

        if np.array_equal(rgb, [0, 0, 0]):
            return rhomin * np.zeros(numIntervals)

        if np.array_equal(rgb, [1, 1, 1]):
            return rhomax * np.ones(numIntervals)

        # Scale RGB values to between 0-1 and remove
        # gamma correction.
        for i in range(3):
            rgb[i] = rgb[i] / 255.0
            if rgb[i] < 0.04045:
                rgb[i] = rgb[i] / 12.92
            else:
                rgb[i] = math.pow((rgb[i] + 0.055) / 1.055, 2.4)

        rho0 = 0.01 * np.ones(numIntervals)

        def loss_fn(rho):
            return np.sum(np.diff(rho) ** 2)

        # Define constraints and bounds.
        cons = [{'type': 'eq', 'fun': lambda rho: (T @ rho) - rgb}, {'type': 'eq', 'fun': lambda rho: rho[0] - 0.01},
                {'type': 'ineq', 'fun': lambda rho: rho[-1] - 0.4}]
        bounds = [(rhomin, rhomax)] * numIntervals

        minout = minimize(loss_fn, rho0, method='SLSQP', bounds=bounds, constraints=cons)
        print("success: ", minout.success, minout.message)

        return minout.x

    """
    rspectrum_skin estimates the reflectance of a given skin color.
    """

    def rspectrum_skin(rgb):
        T = ImageUtils.read_T_matrix()

        # convert from rgb tuple to list.
        rgb = np.array([rgb[0], rgb[1], rgb[2]], dtype=np.float)
        numIntervals = T.shape[1]
        rhomin = 0.0001
        rhomax = 1

        if np.array_equal(rgb, [0, 0, 0]):
            return rhomin * np.zeros(numIntervals)

        if np.array_equal(rgb, [1, 1, 1]):
            return rhomax * np.ones(numIntervals)

        # Scale RGB values to between 0-1 and remove
        # gamma correction.
        for i in range(3):
            rgb[i] = rgb[i] / 255.0
            if rgb[i] < 0.04045:
                rgb[i] = rgb[i] / 12.92
            else:
                rgb[i] = math.pow((rgb[i] + 0.055) / 1.055, 2.4)

        rho0 = 0.01 * np.ones(numIntervals)

        def loss_fn(rho):
            return np.sum(np.diff(rho) ** 2)

        # Define constraints and bounds.
        cons = [{'type': 'eq', 'fun': lambda rho: (T @ rho) - rgb}, {'type': 'eq', 'fun': lambda rho: rho[0] - 0.01},
                {'type': 'ineq', 'fun': lambda rho: rho[-1] - 0.4}]
        bounds = [(rhomin, rhomax)] * numIntervals

        minout = minimize(loss_fn, rho0, method='SLSQP', bounds=bounds, constraints=cons)
        print("success: ", minout.success, minout.message)

        return minout.x

    """
    sRGB_to_XYZ converts given sRGB array (0-255) to XYZ (0-1) under D65 illuminant.
    """

    def sRGB_to_XYZ(rgb):
        # Convert RGB to [0-1] and remove gamma correction.
        rgb = ImageUtils.remove_gamma_correction(np.array(rgb, dtype=float))
        illuminant_D65 = np.array([0.31270, 0.32900])
        RGB_to_XYZ_matrix = np.array(
            [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
        return colour.RGB_to_XYZ(rgb, illuminant_D65, illuminant_D65, RGB_to_XYZ_matrix, None)

    """
    sRGB_to_XYZ_matrix converts given sRGB array (n,3) (0-255) into XYZ array(n,3) (0-1).
    """

    def sRGB_to_XYZ_matrix(rgbArr):
        rgbArr = ImageUtils.remove_gamma_correction_matrix(rgbArr)
        RGB_to_XYZ_matrix = np.array(
            [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
        return np.transpose(RGB_to_XYZ_matrix @ np.transpose(rgbArr))

    """
    sRGB_to_XYZ converts given XYZ array (0-1) to sRGB (0-255) under D65 illuminant.
    """

    def XYZ_to_sRGB(xyz):
        XYZ_to_RGB_matrix = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560],
                                      [0.0556434, -0.2040259, 1.0572252]])
        illuminant_D65 = np.array([0.31270, 0.32900])
        rgb = colour.XYZ_to_RGB(xyz, illuminant_D65, illuminant_D65, XYZ_to_RGB_matrix, None)
        return ImageUtils.add_gamma_correction(rgb)

    """
    XYZ_to_sRGB_matrix converts given XYZ array (n, 3)(0-1) to sRGB(n,3) (0-255) under D65 illuminant.
    """

    def XYZ_to_sRGB_matrix(xyzArr):
        XYZ_to_RGB_matrix = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560],
                                      [0.0556434, -0.2040259, 1.0572252]])
        srgbArr = np.transpose(XYZ_to_RGB_matrix @ np.transpose(xyzArr))
        return ImageUtils.add_gamma_correction_matrix(srgbArr)

    """
    sRGB_to_uv converts given sRGB array(0-255) to uv(0-1) chromaticity.
    """

    def sRGB_to_uv(srgb):
        xyz = ImageUtils.sRGB_to_XYZ(srgb)
        xy = colour.XYZ_to_xy(xyz)
        return colour.xy_to_Luv_uv(xy)

    """
    to_YCrCb converts given sRGB image to YCrCb image.
    """

    def to_YCrCb(srgbImage):
        return cv2.cvtColor(srgbImage, cv2.COLOR_RGB2YCR_CB)

    """
    to_Lab converts given RGB image to Lab image.
    """

    def to_Lab(rgbImage):
        return cv2.cvtColor(rgbImage, cv2.COLOR_RGB2LAB)

    """
    to_hsv converts given sRGB image to HSV image.
    """

    def to_hsv(srgbImage):
        return cv2.cvtColor(srgbImage, cv2.COLOR_RGB2HSV)

    """
    to_hLS converts given RGB image to HlS image.
    """

    def to_hls(rgbImage):
        return cv2.cvtColor(rgbImage, cv2.COLOR_RGB2HLS)

    """
    to_gray converts given RGB image to Gray image.
    """

    def to_gray(rgbImage):
        return cv2.cvtColor(rgbImage, cv2.COLOR_RGB2GRAY)

    """
    chromatic_adaptation converts given
    """

    def chromatic_adaptation(imagePath, source_white):
        swhite_xyz = ImageUtils.sRGB_to_XYZ_matrix(np.array(source_white))
        d65_xyz = colour.xy_to_XYZ(np.array([0.31270, 0.32900]))

        m_bradford = np.array(
            [[0.8951, 0.2664000, -0.1614000], [-0.7502000, 1.7135000, 0.0367000], [0.0389000, -0.0685000, 1.0296000]])
        m_gain = np.diag((m_bradford @ d65_xyz) / (m_bradford @ swhite_xyz))
        m_transform = np.linalg.inv(m_bradford) @ m_gain @ m_bradford

        # Chromatically adapt given image.
        _, _, img, _ = ImageUtils.read(imagePath)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        flat_img = np.reshape(img, (-1, 3))
        flat_xyz = ImageUtils.sRGB_to_XYZ_matrix(flat_img)
        adapted_xyz = np.transpose(m_transform @ np.transpose(flat_xyz))
        adapted_img = np.clip(ImageUtils.XYZ_to_sRGB_matrix(adapted_xyz), 0, 255).astype(np.uint8)
        img = cv2.cvtColor(np.reshape(adapted_img, img.shape), cv2.COLOR_RGB2BGR)

        print("imgs shape: ", img.shape)
        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("image", 900, 900)
        cv2.imshow("image", img)
        cv2.waitKey(0)

    """
    CCT_to_sRGB returns sRGB value of correlated color temperature(Kelvin).
    """

    def CCT_to_sRGB(cct):
        return np.clip(ImageUtils.XYZ_to_sRGB_matrix(colour.xy_to_XYZ(colour.CCT_to_xy(cct))), 0, 255)

    """
    sRGB_to_CCT returns correlated color temperature(Kelvin) of sRGB color.
    """

    def sRGB_to_CCT(sRGB):
        XYZ = colour.sRGB_to_XYZ(np.array(sRGB) / 255.0)
        xy = colour.XYZ_to_xy(XYZ)
        return colour.xy_to_CCT(xy, 'hernandez1999')

    """
    Temp_to_sRGB returns sRGB value of correlated color temperature(K)
    using Tanner Hallend's algorithm(https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html)
    Algorithm works for temperatures between 100K and 40000K.
    """

    def Temp_to_sRGB(cct):
        cct = float(cct) / 100
        red, green, blue = 0.0, 0.0, 0.0
        if cct <= 66:
            red = 255
            green = 99.4708025861 * math.log(cct) - 161.1195681661
            blue = 0 if cct <= 19 else 138.5177312231 * math.log(cct - 10) - 305.0447927307
        else:
            red = 329.698727446 * math.pow(cct - 60, -0.1332047592)
            green = 288.1221695283 * (math.pow(cct - 60, -0.0755148492))
            blue = 255

        return np.clip([red, green, blue], 0, 255).astype(np.uint8)

    """
    sRGB_to_SD converts given sRGB numpy array
    to a spectral distribution using color science library.
    """

    def sRGB_to_SD(srgb):
        # Convert RGB to [0-1] and remove gamma correction.
        rgb = ImageUtils.remove_gamma_correction(np.array(srgb, dtype=float))

        # D65
        illuminant_RGB = np.array([0.31270, 0.32900])
        illuminant_XYZ = np.array([0.31270, 0.32900])

        RGB_to_XYZ_matrix = np.array(
            [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])

        xyz = colour.RGB_to_XYZ(rgb, illuminant_RGB, illuminant_XYZ, RGB_to_XYZ_matrix, None)
        cmfs = colour.STANDARD_OBSERVERS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(
            colour.SpectralShape(380, 730, 10))
        sd = colour.recovery.XYZ_to_sd_Meng2015(xyz, cmfs, colour.ILLUMINANTS_SDS['D65'])
        return sd.values

    """
    SD_to_RGB converts given spectral distribution values to sRGB using color
    science library.
    """

    def SD_to_RGB(sd_values):
        x = ImageUtils.wavelength_arr()
        assert len(sd_values) == len(x)
        d = {}
        for i, l in enumerate(x):
            d[l] = sd_values[i]

        sd = colour.SpectralDistribution(d)
        xyz = colour.sd_to_XYZ(sd, colour.CMFS['CIE 1931 2 Degree Standard Observer'],
                               colour.ILLUMINANTS_SDS['D65']) / 100.0

        # D65
        illuminant_RGB = np.array([0.31270, 0.32900])
        illuminant_XYZ = np.array([0.31270, 0.32900])
        XYZ_to_RGB_matrix = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560],
                                      [0.0556434, -0.2040259, 1.0572252]])
        rgb = colour.XYZ_to_RGB(xyz, illuminant_XYZ, illuminant_RGB, XYZ_to_RGB_matrix, None)
        return ImageUtils.add_gamma_correction(rgb)

    """
    add_gamma_correction adds gamma correction to given RGB value and
    returns the new value. Input rgb has to be between 0-1.
    """

    def add_gamma_correction(rgb):
        for i in range(3):
            if abs(rgb[i]) < 0.0031308:
                rgb[i] = int(12.92 * abs(rgb[i]) * 255)
            else:
                rgb[i] = int(255 * (1.055 * (math.pow(abs(rgb[i]), 1 / 2.4)) - 0.055))

        return rgb

    """
    wavelength_arr returns the numpy array of wavelengths for which
    we are interested in Spectral distribution.
    """

    def wavelength_arr(self):
        return [i for i in range(380, 731, 10)]

    """
    compute_luminance computes luminance of given sRGB color.
    """

    def compute_luminance(color):
        rgb = ImageUtils.remove_gamma_correction(np.array(color).astype(np.float))
        c = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
        return 1.055 * math.pow(c, 1 / 2.4) - 0.055 if c > 0.0031308 else 12.92 * c

    """
    remove_gamma_correction removes gamma correction from sRGB to given Linear RGB value.
    Input sRGB has to be between 0-255.
    """

    def remove_gamma_correction(rgb):
        for i in range(3):
            rgb[i] = rgb[i] / 255.0
            if abs(rgb[i]) < 0.04045:
                rgb[i] = abs(rgb[i]) / 12.92
            else:
                rgb[i] = math.pow((abs(rgb[i]) + 0.055) / 1.055, 2.4)
        return rgb

    """
    numpy version of removing gamma correction to given array of RGB colors
    that have values between 0-255.
    """

    def remove_gamma_correction_matrix(rgbArr):
        rgbArr = (rgbArr / 255.0).astype(np.float)
        return np.where(rgbArr < 0.04045, rgbArr / 12.92, np.power((rgbArr + 0.055) / 1.055, 2.4)).astype(np.float)

    """
    numpy version of adding gamma correction to given array of RGB colors
    that have values between 0-1.
    """

    def add_gamma_correction_matrix(rgbArr):
        return np.where(rgbArr < 0.0031308, 12.92 * rgbArr * 255,
                        255 * (1.055 * (np.power(rgbArr, 1 / 2.4)) - 0.055)).astype(int)

    """
    geometric_mean_mixing takes input as the given hex colors and then returns
    the color mix (geometric mean of reflectances).
    """

    def geometric_mean_mixing(c1, c2, alpha):
        rgb1, rgb2 = ImageUtils.color(c1), ImageUtils.color(c2)
        T = ImageUtils.read_T_matrix()
        rgb = np.matmul(T,
                        np.power(ImageUtils.rspectrum_lhtss(rgb1), alpha) * np.power(ImageUtils.rspectrum_lhtss(rgb2),
                                                                                     1 - alpha))
        return 255 * rgb
        return ImageUtils.add_gamma_correction(rgb)

    """
    read_T_matrix reads the T matrix CSV containing T matrix used for predicting
    reflectance spectrum for a given color. Refer to http://scottburns.us/subtractive-color-mixture/
    for more details.
    Returned T is a (3,36) numpy array converting reflectance to D65 weighted linear rgb.
    """

    def read_T_matrix(self):
        T_matrix = []
        with open("T_matrix.csv") as f:
            csv_reader = csv.reader(f, delimiter=",")
            rows = []
            for i, row in enumerate(csv_reader):
                if i == 0:
                    continue
                rows.append(row[1:])

            return np.stack(rows, axis=0).astype(np.float)

    """
    R_foundation_depth given the reflectance and transmittance of the given foundation matrix
    at given depth percent (between 0-1 inclusive).
    """

    def R_foundation_depth(R_foundation, x_percent):
        # Assume 2 mm is the maximum depth of the foundation.
        D = 2
        a = 0.5 * ((1 / R_foundation) + R_foundation)
        b = np.sqrt((a ** 2) - 1)

        rho = R_foundation * 0.99
        S = (np.arctanh(b / (a - rho)) - np.arctanh(b / a)) / (b * D)
        K = S * (a - 1)

        # Find reflectance and transmittance at given depth.
        x = x_percent * D
        R = np.sinh(b * S * x) / (a * np.sinh(b * S * x) + b * np.cosh(b * S * x))
        T = b / (a * np.sinh(b * S * x) + b * np.cosh(b * S * x))

        return R, T

    """
    plot_reflectance is a rest function to plot the reflectance of
    an RGB color (in hex format) for different optical depths ranging between 0.1 to 2 mm.
    """

    def plot_reflectance(hexColors):
        x = ImageUtils.wavelength_arr()
        for hexColor in hexColors:
            rho = ImageUtils.sRGB_to_SD(ImageUtils.color(hexColor))
            plt.plot(x, rho, label=hexColor, color=hexColor, linewidth=2)

        plt.legend()
        plt.show()

    """
    plot_skin_spectra will read a database of skin spectra and plot it.
    """

    def plot_skin_spectra(self):
        with open("skin_spectra.csv") as f:
            csv_reader = csv.reader(f, delimiter=",")
            x = None
            for i, row in enumerate(csv_reader):
                g = np.array(row[2:]).astype(np.float)
                if i == 0:
                    x = g
                elif (i > 0 * 482 and i < 4 * 482) or (i >= 7 * 482 and i <= 9 * 482):
                    plt.plot(x, g, linewidth=2)
        plt.show()

    """
    save_skin_spectra_uv will convert the reflectance spectrums of skin spectra
    to uv chromaticity and save it.
    """

    def save_skin_spectra_uv(self):
        skin_chrs = []
        with open("skin_spectra.csv") as f:
            csv_reader = csv.reader(f, delimiter=",")
            x = ImageUtils.wavelength_arr()
            for i, row in enumerate(csv_reader):
                if i == 0:
                    continue
                rho = np.array(row[4:-1]).astype(np.float)
                if (i > 0 * 482 and i < 4 * 482) or (i >= 7 * 482 and i <= 9 * 482):
                    d = {}
                    for k, l in enumerate(x):
                        d[l] = rho[k]

                    sd = colour.SpectralDistribution(d)
                    xyz = colour.colorimetry.sd_to_XYZ_integration(sd, colour.CMFS[
                        'CIE 1931 2 Degree Standard Observer'].copy().align(colour.SpectralShape(380, 730, 10)),
                                                                   colour.ILLUMINANTS_SDS['D65'].copy().align(
                                                                       colour.SpectralShape(380, 730, 10))) / 100.0
                    xy = colour.XYZ_to_xy(xyz)
                    uv = colour.xy_to_Luv_uv(xy)
                    skin_chrs.append(list(uv))

        plt.scatter(*zip(*skin_chrs))
        plt.show()

        with open("skin_uv.json", "w") as f:
            json.dump(skin_chrs, f)

    """
    plot_foundation_depth will plot given foundation at different thickness
    levels. We assume that the given foundation SD is at inifinite optical depth
    and is therefore opaque.
    """

    def plot_foundation_depth(skinColor, hexColor):
        x = ImageUtils.wavelength_arr()
        R_skin = ImageUtils.sRGB_to_SD(ImageUtils.color(skinColor))
        R_foundation = ImageUtils.sRGB_to_SD(ImageUtils.color(hexColor))
        for x_percent in [0.01, 0.05, 0.08, 0.1, 0.2, 0.3, 0.5, 1]:
            rho_f, T_f = ImageUtils.R_foundation_depth(R_foundation, x_percent)
            # rho_mix = np.power(np.power(R_skin,0.85) * np.power(rho_f,0.5), 1)
            # rho_mix = 0.0*R_skin + rho_f
            Rs = 0.1
            rho_mix = (1 - Rs) * (rho_f + ((T_f ** 2) * R_skin) / (1 - (R_skin * rho_f))) + Rs
            color = ImageUtils.RGB2HEX(ImageUtils.SD_to_RGB(rho_mix))
            plt.plot(x, rho_mix, label=color + "-" + str(x_percent), color=color, linewidth=2)

        plt.legend()
        plt.show()

    """
    hash_tuple provides a string representation of the given tuple
    to use as key when saving dictionary as JSON.
    """

    def hash_tuple(t):
        return str(t[0]) + "-" + str(t[1]) + "-" + str(t[2])

    """
    reverse_hash_tuple returns a tuple from given string representing the dictionary
    key when saving to JSON.
    """

    def reverse_hash_tuple(tstr):
        tvals = tstr.split("-")
        return (int(tvals[0]), int(tvals[1]), int(tvals[2]))

    """
    compute_all_reflectances will compute reflectance (infinite optical depth)
    for all colors in the RGB space and store them in a JSON file.
    """

    def compute_all_reflectances(self):
        d = {}
        total = 256 * 256 * 256
        print("Total: ", total)
        next_milestone = 0
        for i in range(256):
            for j in range(256):
                for k in range(256):
                    rho_infinity = ImageUtils.rspectrum_lhtss((i, j, k))
                    d[ImageUtils.hash_tuple((i, j, k))] = rho_infinity.tolist()
                    if int(len(d) / total) * 100 >= next_milestone:
                        print(str(next_milestone) + "% complete")
                        next_milestone += 1

        with open("reflectance.json", "w") as f:
            json.dump(d, f)

    """
    random_color generates a random RGB color each time it is called.
    """

    def random_color(self):
        return tuple(np.random.choice(range(256), size=3))

    """
    RGB2HEX converts RGB tuple to Hex string.
    """

    def RGB2HEX(color):
        return "#{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))

    """
    sRGBtoHSV converts given sRGB array (n by 3) into (n, 3) HSV array.
    """

    def sRGBtoHSV(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_RGB2HSV),
                          (-1, 3))

    """
    sRGBtoHLS converts given sRGB array (n by 3) into (n, 3) HLS array.
    """

    def sRGBtoHLS(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_RGB2HLS),
                          (-1, 3))

    """
    sRGBtoGray converts given RGB array (n by 3) into (1 by 1) Gray array.
    """

    def sRGBtoGray(colorArr):
        return cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8),
                            cv2.COLOR_RGB2GRAY).astype(np.float)[0][0]

    """
    Converts given HSV/HLS OpenCV values (H=0-179, S=0-255, V=0-255) to preferred values (H=0-360, S=0-100, 
    V=0-100).Will works for HLS input also because L and S have the same ranges and H is the same for both HSV and HLS.
    """
    def toHSVPreferredRange(hsv):
        h = hsv[0]*2
        s = round(hsv[1] * (100.0 / 255.0), 2)
        v = round(hsv[2] * (100.0 / 255.0), 2)
        return np.array([h, s, v])

    """
    Returns image colorfulness of given srgb image per algorithm in 
    https://pyimagesearch.com/2017/06/05/computing-image-colorfulness-with-opencv-and-python/.
    """

    def image_colorfulness(image):
        # split the image into its respective RGB components
        R = image[:, :, 0].astype("float")
        G = image[:, :, 1].astype("float")
        B = image[:, :, 2].astype("float")

        # compute rg = R - G
        rg = np.absolute(R - G)
        # compute yb = 0.5 * (R + G) - B
        yb = np.absolute(0.5 * (R + G) - B)
        # compute the mean and standard deviation of both `rg` and `yb`
        (rbMean, rbStd) = (np.mean(rg), np.std(rg))
        (ybMean, ybStd) = (np.mean(yb), np.std(yb))
        # combine the mean and standard deviations
        stdRoot = np.sqrt((rbStd ** 2) + (ybStd ** 2))
        meanRoot = np.sqrt((rbMean ** 2) + (ybMean ** 2))
        # derive the "colorfulness" metric and return it
        return stdRoot + (0.3 * meanRoot)

    """
    HSVtosRGB converts given HSV array (n by 3) into (n by 3) sRGB array.
    """

    def HSVtosRGB(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_HSV2RGB),
                          (-1, 3))

    """
    sRGBtoLab converts given sRGB array (n by 3) into (n, 3) Lab array.
    """

    def sRGBtoLab(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_RGB2LAB),
                          (-1, 3))

    """
    LabtosRGB converts given Lab array (n by 3) into (n, 3) sRGB array.
    The Lab input here is assumed to be in the cv2 range i.e. (L=0-255, a=0-255, b=0-255).
    """

    def LabtosRGB(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_LAB2RGB),
                          (-1, 3))

    """
    LabTosRGBConventional converts given Lab array (n by 3) into (n, 3) display P3 RGB array. The Lab input here is 
    assumed to be in the conventional range (L=0-100, a=-128-127, b=-128-127). We convert it to cv2 range first i.e. 
    (L=0-255, a=0-255, b=0-255) and then convert it to RGB display P3.
    """

    def LabTosRGBConventional(labArr):
        lab = np.array([labArr[0] * (255.0 / 100.0), labArr[1] + 128.0, labArr[2] + 128.0])
        return ImageUtils.LabtosRGB(lab)

    """
    sRGBtoYCrCb converts given sRGB array (n by 3) into (n, 3) YCrCb array.
    """

    def sRGBtoYCrCb(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_RGB2YCR_CB),
                          (-1, 3))

    """
    YCrCbtosRGB converts given YCrCb array (n by 3) into (n, 3) sRGB array.
    """

    def YCrCbtosRGB(colorArr):
        return np.reshape(cv2.cvtColor(np.reshape(colorArr,
                                                  (-1, 3))[np.newaxis, :, :].astype(np.uint8), cv2.COLOR_YCR_CB2RGB),
                          (-1, 3))

    """
    Converts given sRGB array (1,3) to munsell color (string).
    """

    def sRGBtoMunsell(sRGB) -> np.ndarray:
        return ImageUtils.displayP3toMunsell(sRGB)
        sRGB = sRGB / 255.0
        C = colour.CCS_ILLUMINANTS['cie_2_1931']['C']
        try:
            return colour.xyY_to_munsell_colour(colour.XYZ_to_xyY(colour.sRGB_to_XYZ(sRGB, C)))
        except Exception as e:
            print("e: ", e)
            return "None"

    """
    displayP3toMunsell converts given display P3 array (1,3) to munsell color (string).
    """

    def displayP3toMunsell(displayP3):
        try:
            return colour.xyY_to_munsell_colour(colour.XYZ_to_xyY(ImageUtils.displayP3toXYZ(displayP3)))
        except Exception as e:
            print("display P3 to Munsell exception: ", e)
            return "None"

    """
    flatten_rgb flattens the given RGB tuple into its corresponding index number from 1 to 256*256*256.
    """

    def flatten_rgb(rgb):
        return rgb[0] * 256 * 256 + rgb[1] * 256 + rgb[2] + 1

    """
    delta_e_mask returns delta_e_cie2000 between given masks for given sRGB image.
    """

    def delta_e_mask(image, mask1, mask2):
        return ImageUtils.delta_cie2000(np.mean(image[mask1], axis=0), np.mean(image[mask2], axis=0))

    """
    delta_e_mask_matrix returns delta_e_cie2000 between a given color and a mask for given sRGB image. Returns an 
    array of delta values of each point in the mask.
    """

    def delta_e_mask_matrix(sRGB, rgbColors):
        rgbColors = np.vstack([rgbColors, sRGB])
        labColors = ImageUtils.sRGBtoLab(rgbColors).astype(np.float)
        labColors[:, 0] = labColors[:, 0] * (100.0 / 255.0)
        labColors[:, 1] = labColors[:, 1] - 128
        labColors[:, 2] = labColors[:, 2] - 128

        lab = labColors[-1]
        labColors = labColors[:-1]

        return color_diff_matrix.delta_e_cie2000(lab, labColors)

    """
    Calculates the Delta E (CIE2000) of two sRGB colors (range 0-255).
    """

    def delta_cie2000(srgb_a, srgb_b):
        lab_a = convert_color(
            colormath.color_objects.sRGBColor(srgb_a[0], srgb_a[1], srgb_a[2], True),
            colormath.color_objects.LabColor)
        lab_b = convert_color(
            colormath.color_objects.sRGBColor(srgb_b[0], srgb_b[1], srgb_b[2], True),
            colormath.color_objects.LabColor)
        return delta_e_cie2000(lab_a, lab_b)

    """
    Delta cie2000 computation using colour science library which is apparently faster than colormath library per this answer
    https://stackoverflow.com/questions/57224007/how-to-compute-the-delta-e-between-two-images-using-opencv. This method
    computes the value between a single rgb array and an an rgb image. If arr1 is (1 by 3) and arr_2 is (100, 300, 
    3) then the returned result will have dimensions (100, 100).
    """

    def delta_cie2000_matrix_v2(arr1_rgb, arr2_rgb):
        arr1_lab = np.reshape(cv2.cvtColor(arr1_rgb[np.newaxis, :, :].astype(np.float32) / 255, cv2.COLOR_RGB2LAB),
                              (1, 3))
        arr2_lab = cv2.cvtColor(arr2_rgb.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)
        return colour.delta_E(arr1_lab, arr2_lab, method='CIE 2000')

    """
    Return delta e cie2000 between two (1,3) numpy array RGB colors.
    """

    def delta_cie2000_v2(arr1_rgb, arr2_rgb):
        arr1_rgb = np.reshape(arr1_rgb, (1,3))
        arr2_rgb = np.reshape(arr2_rgb, (1, 3))

        arr1_lab = np.reshape(cv2.cvtColor(arr1_rgb[np.newaxis, :, :].astype(np.float32) / 255, cv2.COLOR_RGB2LAB),
                              (1, 3))
        arr2_lab = np.reshape(cv2.cvtColor(arr2_rgb[np.newaxis, :, :].astype(np.float32) / 255, cv2.COLOR_RGB2LAB),
                              (1, 3))
        return colour.delta_E(arr1_lab, arr2_lab, method='CIE 2000')[0]

    """
    lab_colors converts given sRGB array(n,3) into LAB array(n,3).
    """

    def lab_colors(rgbColors):
        labColors = ImageUtils.sRGBtoLab(rgbColors).astype(np.float)
        labColors[:, 0] = labColors[:, 0] * (100.0 / 255.0)
        labColors[:, 1] = labColors[:, 1] - 128
        labColors[:, 2] = labColors[:, 2] - 128
        return labColors

    """
    average_delta_e_cie2000_masks returns average delta_e_cie2000 difference between two colors arrays which are (n1,
    3) and (n2,3) and n1 != n2. The difference is taken between min(n1,n2) elements that are randomly chosen from 
    each array.
    """

    def average_delta_e_cie2000_masks(colors1, colors2):
        n1 = colors1.shape[0]
        n2 = colors2.shape[0]
        n = min(n1, n2)

        i1 = random.sample(range(n1), k=n)
        i2 = random.sample(range(n2), k=n)
        return np.mean(ImageUtils.delta_e_cie2000_vectors(colors1[i1], colors2[i2]))

    """
    delta_e_cie2000_vectors calculates the Delta E (CIE2000) distance matrix for given vectors (n,3) of sRGB colors 
    of type np.float.
    """

    def delta_e_cie2000_vectors(X1, X2, Kl=1, Kc=1, Kh=1):
        X1 = ImageUtils.lab_colors(X1)
        X2 = ImageUtils.lab_colors(X2)

        avg_Lp = (X1[:, 0] + X2[:, 0]) / 2.0

        C1 = np.sqrt(np.sum(np.power(X1[:, 1:], 2), axis=1))
        C2 = np.sqrt(np.sum(np.power(X2[:, 1:], 2), axis=1))

        avg_C1_C2 = (C1 + C2) / 2.0

        G = 0.5 * (
                1
                - np.sqrt(
            np.power(avg_C1_C2, 7.0)
            / (np.power(avg_C1_C2, 7.0) + np.power(25.0, 7.0))
        )
        )

        a1p = (1.0 + G) * X1[:, 1]
        a2p = (1.0 + G) * X2[:, 1]

        C1p = np.sqrt(np.power(a1p, 2) + np.power(X1[:, 2], 2))
        C2p = np.sqrt(np.power(a2p, 2) + np.power(X2[:, 2], 2))

        avg_C1p_C2p = (C1p + C2p) / 2.0

        h1p = np.degrees(np.arctan2(X1[:, 2], a1p))
        h1p += (h1p < 0) * 360

        h2p = np.degrees(np.arctan2(X2[:, 2], a2p))
        h2p += (h2p < 0) * 360

        avg_Hp = (((np.fabs(h1p - h2p) > 180) * 360) + h1p + h2p) / 2.0

        T = (
                1
                - 0.17 * np.cos(np.radians(avg_Hp - 30))
                + 0.24 * np.cos(np.radians(2 * avg_Hp))
                + 0.32 * np.cos(np.radians(3 * avg_Hp + 6))
                - 0.2 * np.cos(np.radians(4 * avg_Hp - 63))
        )

        diff_h2p_h1p = h2p - h1p
        delta_hp = diff_h2p_h1p + (np.fabs(diff_h2p_h1p) > 180) * 360
        delta_hp -= (h2p > h1p) * 720

        delta_Lp = X2[:, 0] - X1[:, 0]
        delta_Cp = C2p - C1p
        delta_Hp = 2 * np.sqrt(C2p * C1p) * np.sin(np.radians(delta_hp) / 2.0)

        S_L = 1 + (
                (0.015 * np.power(avg_Lp - 50, 2))
                / np.sqrt(20 + np.power(avg_Lp - 50, 2.0))
        )
        S_C = 1 + 0.045 * avg_C1p_C2p
        S_H = 1 + 0.015 * avg_C1p_C2p * T

        delta_ro = 30 * np.exp(-(np.power(((avg_Hp - 275) / 25), 2.0)))
        R_C = np.sqrt(
            (np.power(avg_C1p_C2p, 7.0))
            / (np.power(avg_C1p_C2p, 7.0) + np.power(25.0, 7.0))
        )
        R_T = -2 * R_C * np.sin(2 * np.radians(delta_ro))

        return np.sqrt(
            np.power(delta_Lp / (S_L * Kl), 2)
            + np.power(delta_Cp / (S_C * Kc), 2)
            + np.power(delta_Hp / (S_H * Kh), 2)
            + R_T * (delta_Cp / (S_C * Kc)) * (delta_Hp / (S_H * Kh))
        )

    """
    Calculates the Delta E (CIE2000) distance matrix for given matrix of colors. The matrix is shape (n, 3) where n 
    is the number of colors and type np.float.
    """

    def delta_e_cie2000_matrix(X, Kl=1, Kc=1, Kh=1):
        nSamples = X.shape[0]
        L1mat = np.repeat(np.reshape(X[:, 0], (1, nSamples)), nSamples, axis=0)
        L2mat = np.repeat(np.reshape(X[:, 0], (nSamples, 1)), nSamples, axis=1)
        avg_Lp = (L1mat + L2mat) / 2.0

        C1mat = np.repeat(np.reshape(np.sqrt(np.sum(X[:, 1:] ** 2, axis=1)), (1, nSamples)), nSamples, axis=0)
        C2mat = np.repeat(np.reshape(np.sqrt(np.sum(X[:, 1:] ** 2, axis=1)), (nSamples, 1)), nSamples, axis=1)

        avg_C1_C2 = (C1mat + C2mat) / 2.0

        G = 0.5 * (1 - np.sqrt(avg_C1_C2 ** 7.0 / ((avg_C1_C2 ** 7.0) + 25.0 ** 7.0)))

        a1p = (1.0 + G) * np.repeat(np.reshape(X[:, 1], (1, nSamples)), nSamples, axis=0)
        a2p = (1.0 + G) * np.repeat(np.reshape(X[:, 1], (nSamples, 1)), nSamples, axis=1)

        C1p = np.sqrt(a1p ** 2 + np.repeat(np.reshape(X[:, 2] ** 2, (1, nSamples)), nSamples, axis=0))
        C2p = np.sqrt(a2p ** 2 + np.repeat(np.reshape(X[:, 2] ** 2, (nSamples, 1)), nSamples, axis=1))

        avg_C1p_C2p = (C1p + C2p) / 2.0

        h1p = np.degrees(np.arctan2(np.repeat(np.reshape(X[:, 2], (1, nSamples)), nSamples, axis=0), a1p))
        h1p += (h1p < 0) * 360
        h2p = np.degrees(np.arctan2(np.repeat(np.reshape(X[:, 2], (nSamples, 1)), nSamples, axis=1), a2p))
        h2p += (h2p < 0) * 360
        avg_Hp = (((np.fabs(h1p - h2p) > 180) * 360) + h1p + h2p) / 2.0

        T = (
                1
                - 0.17 * np.cos(np.radians(avg_Hp - 30))
                + 0.24 * np.cos(np.radians(2 * avg_Hp))
                + 0.32 * np.cos(np.radians(3 * avg_Hp + 6))
                - 0.2 * np.cos(np.radians(4 * avg_Hp - 63))
        )

        diff_h2p_h1p = h2p - h1p
        delta_hp = diff_h2p_h1p + (np.fabs(diff_h2p_h1p) > 180) * 360
        delta_hp -= (h2p > h1p) * 720

        delta_Lp = np.repeat(np.reshape(X[:, 0], (nSamples, 1)), nSamples, axis=1) - np.repeat(
            np.reshape(X[:, 0], (1, nSamples)), nSamples, axis=0)
        delta_Cp = C2p - C1p
        delta_Hp = 2 * np.sqrt(C2p * C1p) * np.sin(np.radians(delta_hp) / 2.0)

        S_L = 1 + (
                (0.015 * ((avg_Lp - 50) ** 2))
                / np.sqrt(20 + ((avg_Lp - 50) ** 2.0))
        )
        S_C = 1 + 0.045 * avg_C1p_C2p
        S_H = 1 + 0.015 * avg_C1p_C2p * T

        delta_ro = 30 * np.exp(-(((avg_Hp - 275) / 25) ** 2.0))
        R_C = np.sqrt(
            ((avg_C1p_C2p) ** 7.0)
            / ((avg_C1p_C2p) ** 7.0 + 25.0 ** 7.0))
        R_T = -2 * R_C * np.sin(2 * np.radians(delta_ro))

        return np.sqrt(
            (delta_Lp / (S_L * Kl)) ** 2
            + (delta_Cp / (S_C * Kc)) ** 2
            + (delta_Hp / (S_H * Kh)) ** 2
            + R_T * (delta_Cp / (S_C * Kc)) * (delta_Hp / (S_H * Kh))
        )

    """
    Kmedoids implements Kmedoids algorithm (using given distance matrix) to form k clusters for given colors. 
    Returned cluster matrix is of size (k, n).
    """

    def Kmedoids(colors, dMatrix, k):
        n = dMatrix.shape[0]

        medIndices = random.sample(range(n), k)
        costMap = {}
        totalCost = 0.0
        while True:
            # Assign labels to non medoid data points.
            # print ("medIndices: ", medIndices)
            clusterMap = {}
            odMap = {}
            for i in range(n):
                id = np.argmin(dMatrix[i, medIndices])
                if medIndices[id] not in clusterMap:
                    clusterMap[medIndices[id]] = set()
                clusterMap[medIndices[id]].add(i)
                odMap[i] = medIndices[id]

            bestCost = 0.0
            for m in medIndices:
                bestCost += np.sum(dMatrix[m, list(clusterMap[m])])
            totalCost = bestCost

            # Compute total cost after swapping each non medoid with each medoid.
            bestPair = (-1, -1)
            medIndicesSet = set(medIndices)
            for m in medIndices:
                for i in range(n):
                    if i in medIndicesSet:
                        continue

                    # Swap i with m and compute cost of configuration.
                    odc = odMap[i]
                    clusterMap[i] = clusterMap[m].copy()
                    odMap[i] = i
                    del clusterMap[m]
                    if odc != m:
                        odMap[m] = odc
                        clusterMap[i].add(i)
                        clusterMap[i].remove(m)
                        clusterMap[odc].remove(i)
                        clusterMap[odc].add(m)
                    else:
                        odMap[m] = i

                    cost = 0.0
                    for r in clusterMap:
                        cost += np.sum(dMatrix[r, list(clusterMap[r])])

                    if cost < bestCost:
                        # Save current best pair.
                        bestCost = cost
                        bestPair = (m, i)

                    # Swap i and m back.
                    odMap[m] = m
                    odMap[i] = odc
                    clusterMap[m] = clusterMap[i].copy()
                    del clusterMap[i]
                    if odc != m:
                        clusterMap[odc].remove(m)
                        clusterMap[odc].add(i)
                        clusterMap[m].add(m)
                        clusterMap[m].remove(i)

            if bestPair == (-1, -1) or math.isclose(totalCost, bestCost, rel_tol=1e-3):
                # print ("Kmedoids complete")
                break

            # Update medIndices for next iteration.
            medIndicesSet.remove(bestPair[0])
            medIndicesSet.add(bestPair[1])
            medIndices = list(medIndicesSet).copy()

        medoids = [colors[idx] for idx in medIndices]
        return medoids, clusterMap, medIndices

    """
    clusterCost returns the cost of using given medoids as cluster centers (for given comparison mask) as well as the 
    resultant masks.
    """

    def clusterCost(image, cmpMask, medoids):
        allColors = image[cmpMask]
        n = allColors.shape[0]
        k = len(medoids)

        newClusters = np.zeros((k, n))
        for i in range(k):
            newClusters[i, :] = ImageUtils.delta_e_mask_matrix(medoids[i], allColors)

        clusterIndices = np.argmin(newClusters, axis=0)
        allCords = np.transpose(np.nonzero(cmpMask))
        cost = 0.0
        allMasks = []
        allIndices = []
        for i in range(k):
            # Points in mask closest to ith medoid.
            clusterMask = clusterIndices == i
            cm = np.zeros(cmpMask.shape, dtype=bool)
            cm[allCords[clusterMask][:, 0], allCords[clusterMask][:, 1]] = True
            cost += np.mean(ImageUtils.delta_e_mask_matrix(medoids[i], image[cm]))
            allMasks.append(cm)
            allIndices.append(i)

        return cost, allMasks, allIndices

    """
    best_clusters returns k colors that best represent the given colors against given mask cmpMask (for given image) 
    as well as the corresponding masks. It was written to be called by the method in the face class.
    """

    def best_clusters(colors, image, cmpMask, k, numIters=1000, tol=2):
        n = colors.shape[0]
        dMatrix = np.zeros((n, n))
        for i in range(n):
            dMatrix[i, :] = ImageUtils.delta_e_mask_matrix(colors[i], colors)

        def hash(mlist):
            return ''.join(sorted([ImageUtils.RGB2HEX(m) for m in mlist]))

        mdHashSet = set()
        bestMedoids = []
        bestMasks = []
        bestIndices = []
        minCost = 10000.0
        for iter in range(numIters):
            try:
                medoids, _, _ = ImageUtils.Kmedoids(colors, dMatrix, k=k)
                mdHash = hash(medoids)
                if mdHash in mdHashSet:
                    continue
                mdHashSet.add(mdHash)
                cost, allMasks, allIndices = ImageUtils.clusterCost(image, cmpMask, medoids)
                if cost < minCost:
                    minCost = cost
                    bestMedoids = medoids.copy()
                    bestMasks = allMasks.copy()
                    bestIndices = allIndices.copy()
                    if cost <= tol:
                        break
            except Exception as e:
                print(e)

        return bestMedoids, bestMasks, bestIndices, minCost

    """
    boundaries returns a list of masks that each represent a cluster of boundary points associated with given mask.
    """

    def find_boundaries(mask):
        from scipy import ndimage

        # Find all distinct clusters in given mask.
        labelImage, labels = ndimage.label(mask)
        sizes = ndimage.sum(mask, labelImage, range(labels + 1))
        clusterSizeCutOff = (0.1 / 100.0) * np.count_nonzero(mask)
        indices = np.transpose(np.argwhere(sizes > clusterSizeCutOff))
        allMasks = np.repeat(labelImage[:, :, np.newaxis], len(indices), axis=2) == indices

        # Dominant mask, one with largest number of points.
        # domMask = allMasks[:, :, np.argmax(np.sum(np.where(allMasks, np.repeat(self.beta[:, :, np.newaxis], len(indices), axis=2), 0), axis=(0,1))/sizes[indices])]

        # Find boundary mask of each cluster.
        flatIndicesList = [item for sublist in indices for item in sublist]
        allBoundaryMasks = []
        for idx in range(len(flatIndicesList)):
            clusterMask = allMasks[:, :, idx]
            contours, _ = cv2.findContours(cv2.threshold((200 * clusterMask).astype(np.uint8), 127, 255, 0)[1],
                                           cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cImg = np.zeros(mask.shape)
            cv2.drawContours(cImg, contours, 0, color=255, thickness=3)
            allBoundaryMasks.append(cImg == 255)

        assert len(allBoundaryMasks) > 0
        return allBoundaryMasks

    """
    Divides mask periodically along x-axis and then returns all mean coordinates of resulting boundary masks.
    """

    def mean_coordinates_of_mask(mask):
        # We break the mask to make it more likely that each submask boundary is convex
        # and therefore the mean coordinate is more accurate representation of the
        # submask polygon.
        brokenMask = ImageUtils.break_mask_periodically(mask.copy())

        # Find boundaries will return the boundary mask clusters associated
        # with the given broken mask. We find the mean coordinate of each boundary
        # and return the list.
        allBoundaryMasks = ImageUtils.find_boundaries(brokenMask)
        meanCoordinateList = []
        for m in allBoundaryMasks:
            meanCoordinateList.append(ImageUtils.mean_coordinate(m))
        return meanCoordinateList

    """
    Breaks given mask periodically along x-axis to ensure that when cv2.findContours is applied later, we don't get 
    large concave boundaries in the result that then result in incorrect mean points.
    """

    def break_mask_periodically(mask):
        coordinates = np.argwhere(mask)
        ymin, xmin = np.min(coordinates, axis=0)
        ymax, xmax = np.max(coordinates, axis=0)

        # If xmax-min < delta, then we don't break up the mask
        # as applying findContours will give us accurate mean point
        # representing the mask.
        delta = 20
        newMask = mask.copy()
        for x in range(xmin, xmax, delta):
            newMask[:, x] = False
        return newMask

    """
    Performs Kmeans clustering of given mask using diffImg and returns 2 submasks. The ordering of submasks returned 
    is by decreasing mean value of diffImg. diffImg has dimensions (W,H).
    """

    def Kmeans_1d(diffImg, mask: np.ndarray) -> object:
        from sklearn.cluster import KMeans

        maskCords = np.transpose(np.nonzero(mask))
        data = diffImg[mask].reshape((-1, 1))

        kmeans = KMeans(n_clusters=2).fit(data)
        labels = kmeans.predict(data)
        c1 = kmeans.cluster_centers_[0][0]
        c2 = kmeans.cluster_centers_[1][0]

        # first mask.
        f1Mask = np.zeros(diffImg.shape, dtype=bool)
        xArr = maskCords[labels == 0][:, 0]
        yArr = maskCords[labels == 0][:, 1]
        f1Mask[xArr, yArr] = True

        # second mask.
        f2Mask = np.zeros(diffImg.shape, dtype=bool)
        xArr = maskCords[labels == 1][:, 0]
        yArr = maskCords[labels == 1][:, 1]
        f2Mask[xArr, yArr] = True

        return ((f1Mask, c1), (f2Mask, c2)) if np.mean(diffImg[f1Mask]) > np.mean(diffImg[f2Mask]) else (
            (f2Mask, c2), (f1Mask, c1))

    """
    Returns mask direction by calculating the number of points to the left and right of the nose center of the given 
    mask. The calculation uses a coordinate system whose X axis is parallel to the line segment between the eyes.
    """

    @staticmethod
    def get_mask_direction(mask: np.ndarray, node_middle_point: np.ndarray, rotation_matrix: np.ndarray,
                           debug_mode: bool) -> MaskDirection:
        mask_coordinates = np.argwhere(mask)
        rel_points_arr = mask_coordinates - node_middle_point
        rel_points_arr = (rotation_matrix @ rel_points_arr.T).T

        num_points_to_left = np.count_nonzero(rel_points_arr[:, 1] < 0)
        num_points_to_right = np.count_nonzero(rel_points_arr[:, 1] > 0)
        num_points_in_center = np.count_nonzero(rel_points_arr[:, 1] == 0)
        if num_points_to_left <= num_points_to_right:
            num_points_to_left += num_points_in_center
        else:
            num_points_to_right += num_points_in_center

        RATIO_MAX_VALUE = 100000

        right_to_left_points_ratio = RATIO_MAX_VALUE if num_points_to_left == 0 else float(num_points_to_right) / float(
            num_points_to_left)
        left_to_right_points_ratio = RATIO_MAX_VALUE if num_points_to_right == 0 else float(num_points_to_left) / float(
            num_points_to_right)

        md = MaskDirection.CENTER
        if left_to_right_points_ratio >= 3:
            md = MaskDirection.LEFT
        elif right_to_left_points_ratio >= 3:
            md = MaskDirection.RIGHT

        if debug_mode:
            print("Mask direction: ", md, " toLeftRatio: ", round(left_to_right_points_ratio, 2), " toRightRatio: ",
                  round(right_to_left_points_ratio, 2))
        return md

    """
    Returns face mask till nose end excluding eyes and eyebrows mask from given contour points. The input face mask 
    till nose end has the eyes and eyebrows included. Each contour is a numpy array of points (X,Y). The mask is 
    constructed for the given image shape [W,H,3]. 
    """

    @staticmethod
    def get_face_mask_till_nose_end(image_shape: tuple, face_till_nose_end_contour_points: np.ndarray,
                                    left_eye_contour_points: np.ndarray, right_eye_contour_points: np.ndarray,
                                    left_eyebrow_contour_points: np.ndarray, right_eyebrow_contour_points: np.ndarray):
        mask_shape = image_shape[:2]

        # Create face mask.
        gray_face = np.zeros(mask_shape)
        cv2.drawContours(gray_face, [face_till_nose_end_contour_points], -1, color=255, thickness=cv2.FILLED)
        face_mask = gray_face == 255

        # Create eyes and eyebrows mask.
        gray_eyes_eyebrows = np.zeros(mask_shape)
        cv2.drawContours(gray_eyes_eyebrows, [left_eye_contour_points, right_eye_contour_points,
                                              left_eyebrow_contour_points, right_eyebrow_contour_points], -1, color=255,
                         thickness=cv2.FILLED)
        eyes_and_eyebrows_mask = gray_eyes_eyebrows == 255

        return np.bitwise_xor(face_mask, eyes_and_eyebrows_mask)

    """
    Returns mouth mask from given contour points The contour is a numpy array of points (X,
    Y) representing the boundary points associated with the face boundary. The mask is constructed for the  given 
    image shape [W,H,3]. 
    """

    @staticmethod
    def get_mask_from_contour_points(image_shape: tuple, contour_points: np.ndarray):
        mask_shape = image_shape[:2]

        # Create face mask.
        gray = np.zeros(mask_shape)
        cv2.drawContours(gray, [contour_points], -1, color=255, thickness=cv2.FILLED)

        return gray == 255

    """
    to_brightImage converts sRGB image to HSV image with H = 0, S = 0 and only brightness values.
    """

    @staticmethod
    def to_brightImage(image):
        hsvImage = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float)
        hsvImage[:, :, 0] = 0
        hsvImage[:, :, 1] = 0
        return hsvImage

    """
    to_satImage converts sRGB image to HSV image with H = 0, V = 0 and only saturation values.
    """

    @staticmethod
    def to_satImage(image):
        hsvImage = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float)
        hsvImage[:, :, 0] = 0
        hsvImage[:, :, 2] = 0
        return hsvImage

    """
    Returns array of hue values associated with a mask for given RGB image.
    """

    @staticmethod
    def hue_values(rgb_image, mask):
        hsv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV).astype(np.float)
        hsv_image[:, :, 0] = hsv_image[:, :, 0]*2
        return hsv_image[:, :, 0][mask]

    """
    bbox returns bounding box (x1, y1, w, h) (top left point, width and height) of given mask.
    """

    @staticmethod
    def bbox(mask):
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        return rmin, cmin, cmax - cmin + 1, rmax - rmin + 1

    """
    Returns the rotation matrix to transform from original coordinates to one that is perpendicular to the line 
    segment joining the eyes.
    """

    @staticmethod
    def rotation_matrix(eye_masks):
        # Eye line.
        left_eye_mask = eye_masks[0] if ImageUtils.bbox(eye_masks[0])[1] <= ImageUtils.bbox(eye_masks[1])[1] else eye_masks[1]
        right_eye_mask = eye_masks[0] if ImageUtils.bbox(eye_masks[0])[1] > ImageUtils.bbox(eye_masks[1])[1] else eye_masks[1]

        left_eye_cords = np.argwhere(left_eye_mask)
        xmax_index = np.argmax(left_eye_cords, axis=0)[1]
        left_max_cord = left_eye_cords[xmax_index]

        right_eye_cords = np.argwhere(right_eye_mask)
        xmin_index = np.argmin(right_eye_cords, axis=0)[1]
        right_min_cord = right_eye_cords[xmin_index]

        left_y, left_x = left_max_cord[0], left_max_cord[1]
        right_y, right_x = right_min_cord[0], right_min_cord[1]
        theta = math.atan(float(left_y - right_y) / float(right_x - left_x))
        rot_matrix = np.array([[math.cos(theta), math.sin(theta)], [-math.sin(theta), math.cos(theta)]])

        return rot_matrix

    """
    show is an internal helper function to display given RGB image.
    """

    @staticmethod
    def show(image, windowName="image"):
        # cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)
        # cv2.resizeWindow(self.windowName, (100, 100))
        # cv2.imshow(self.windowName, cv2.cvtColor(ImageUtils.ResizeWithAspectRatio(image, width=600), cv2.COLOR_RGB2BGR))
        cv2.imshow(windowName, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return cv2.waitKey(0) & 0xFF

    @staticmethod
    def show_gray_img(image, windowName="image"):
        # cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)
        # cv2.resizeWindow(self.windowName, (100, 100))
        # cv2.imshow(self.windowName, cv2.cvtColor(ImageUtils.ResizeWithAspectRatio(image, width=600), cv2.COLOR_RGB2BGR))
        cv2.imshow(windowName, cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
        return cv2.waitKey(0) & 0xFF

    """
    show_mask will display given mask.
    """

    @staticmethod
    def show_mask(image, mask, color=[0, 255, 0]):
        clone = image.copy()
        clone[mask] = np.array(color)
        return ImageUtils.show(clone)


    """
    Returns the mean coordinates of the given image mask.
    """

    def mean_coordinate(mask):
        return np.mean(np.argwhere(mask), axis=0)

    """
    converts a display P3 color to XYZ color.
    """

    def displayP3toXYZ(displayP3):
        conversionMatrix = np.array(
            [[0.486571, 0.265668, 0.198217], [0.228975, 0.691739, 0.079287], [0, 0.045113, 1.043944]]).T
        return ImageUtils.remove_gamma_correction(np.array(displayP3)) @ conversionMatrix

    """
    converts a display P3 color to sRGB color.
    """

    def displayP3tosRGB(displayP3):
        conversionMatrix = np.array([[1.2249, -0.2247, 0], [-0.0420, 1.0419, 0], [-0.0197, -0.0786, 1.0979]]).T
        return ImageUtils.add_gamma_correction(
            ImageUtils.remove_gamma_correction(np.array(displayP3)) @ conversionMatrix)

    """
    Converts a display P3 profile image to sRGB profile image. The input is assumed to be (w, h, 3) in shape and (
    0-255) in range and so will be the output.
    """

    def displayP3tosRGBImage(displayP3Array):
        conversionMatrix = np.array([[1.2249, -0.2247, 0], [-0.0420, 1.0419, 0], [-0.0197, -0.0786, 1.0979]]).T
        return np.clip(ImageUtils.add_gamma_correction_matrix(
            ImageUtils.remove_gamma_correction_matrix(displayP3Array) @ conversionMatrix), 0, 255).astype(np.uint8)

    """
    converts a sRGB color to display P3 color.
    """

    def sRGBtodisplayP3(sRGB):
        conversionMatrix = np.array([[0.8225, 0.1774, 0], [0.0332, 0.9669, 0], [0.0171, 0.0724, 0.9108]])
        return ImageUtils.add_gamma_correction(conversionMatrix @ ImageUtils.remove_gamma_correction(np.array(sRGB)))

    """
    Converts a sRGB profile image to display P3 profile image. The input is assumed to be (w, h, 3) in shape and (
    0-255) in range and so will be the output.
    """

    def sRGBtodisplayP3Image(sRGBArray):
        conversionMatrix = np.array([[0.8225, 0.1774, 0], [0.0332, 0.9669, 0], [0.0171, 0.0724, 0.9108]])
        w, h = sRGBArray.shape[:2]
        print("init shape: ", w, h)
        reshaped_arr = np.reshape(sRGBArray, (-1, 3)).astype(np.float)

        intermediate = conversionMatrix @ ImageUtils.remove_gamma_correction_matrix(reshaped_arr).T
        final_arr = np.clip(ImageUtils.add_gamma_correction_matrix(intermediate.T), 0, 255).astype(np.uint8).reshape(w,
                                                                                                                   h,3)
        print("final shape: ", final_arr.shape)
        return final_arr

    """
    Breaks image of given mask to smaller clusters based on brightness and returns mean skin tone for each cluster. 
    The returned skin tones are in decreasing order of brightness.
    """

    def smaller_cluster_skin_tones(image, mask):

        bright_image = np.max(image, axis=2).astype(float)
        total_points = np.count_nonzero(mask)

        # Break mask into smaller clusters.
        max_brightness = int(np.max(bright_image[mask]))
        min_brightness = int(np.min(bright_image[mask]))
        mask_clusters = []
        curr_mask = np.zeros(bright_image.shape, dtype=bool)
        curr_max_brightness = max_brightness
        for brightness in range(max_brightness, min_brightness - 1, -1):
            curr_mask = np.bitwise_or(curr_mask, np.bitwise_and(bright_image == brightness, mask))
            if curr_max_brightness - brightness >= 5:
                mask_clusters.append(curr_mask)
                curr_mask = np.zeros(bright_image.shape, dtype=bool)
                curr_max_brightness = brightness - 1

        if np.count_nonzero(curr_mask) > 0:
            mask_clusters.append(curr_mask)

        all_skin_tones = []
        for m in mask_clusters:
            mean_color_rgb = np.round(np.mean(image[m], axis=0), 2)
            if mean_color_rgb[0] != mean_color_rgb[0]:
                # Nan, skip.
                continue
            hsv = ImageUtils.toHSVPreferredRange(ImageUtils.sRGBtoHSV(mean_color_rgb)[0])
            hls = ImageUtils.toHSVPreferredRange(ImageUtils.sRGBtoHLS(mean_color_rgb)[0])
            gray = ImageUtils.sRGBtoGray(mean_color_rgb)*(100.0/255.0)
            ycrcb = ImageUtils.sRGBtoYCrCb(mean_color_rgb)[0]
            tone = SkinTone(rgb=mean_color_rgb.tolist(), hsv=hsv.tolist(), hls=hls.tolist(), gray=gray, ycrcb=ycrcb,
                            percent_of_face_mask=round(ImageUtils.percentPoints(m, total_points), 2),
                            face_mask=m.copy(),
                            profile=SkinTone.DISPLAY_P3)
            all_skin_tones.append(tone)

        return all_skin_tones

    """
    Computes percent of points in mask relative to given totalPoints.
    """

    def percentPoints(mask, totalPoints):
        return round((np.count_nonzero(mask) / totalPoints) * 100.0, 2)

    """
    Helper function to return the munsell hue letter(e.g. R) from given munsell string.
    """

    def munsell_hue_letter(s):
        match = re.compile("[^\W\d]").search(s)
        return s[match.start():match.end() + 1]

    """
    Helper function to return the munsell hue number (like 7 in 7R) from given munsell string.
    """

    def munsell_hue_number(s):
        match = re.compile("[^\W\d]").search(s)
        return float(s[:match.start()])

    """
    Multiplies the saturation of given rgbImage by given factor.
    """

    def set_saturation(rgbImage, factor):
        hsv = cv2.cvtColor(rgbImage, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * factor, 0, 255).astype(np.uint8)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    """
    Multiplies the each channel of given rgbImage by given factor to increase its brightness.
    """

    def set_brightness(rgbImage, factor):
        return np.clip(np.array(rgbImage).astype(np.float) * factor, 0, 255).astype(np.uint8)

    """
    show_rgb is a function to display given RGB image.
    """

    def show_rgb(image, imgSize=900):
        cv2.namedWindow(ImageUtils.windowName, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(ImageUtils.windowName, imgSize, imgSize)
        cv2.imshow(ImageUtils.windowName, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return cv2.waitKey(0) & 0xFF

    """
    show_image opens up the given image in BGR space.
    """

    def show_image(imagePath):
        _, _, img, _ = ImageUtils.read(imagePath)
        img = np.clip(img, None, 255).astype(np.uint8)
        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("image", 900, 900)
        cv2.imshow("image", img)
        cv2.waitKey(0)

    """
    show_gray opens up the given image in gray space.
    """

    def show_gray(imagePath):
        gray, _, _, hsv = ImageUtils.read(imagePath)
        gray2 = np.clip(gray, None, 255).astype(np.uint8)
        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("image", 900, 900)
        cv2.imshow("image", gray2)
        cv2.waitKey(0)

    def cct(sRGB):
        n = (0.23881 * sRGB[0] + 0.25499 * sRGB[1] - 0.58291 * sRGB[2]) / (
                0.11109 * sRGB[0] - 0.85406 * sRGB[1] + 0.52289 * sRGB[2])
        return 449 * math.pow(n, 3) + 3525 * math.pow(n, 2) + 6823.3 * n + 5520.33

    def print_lab_to_rgb(lab):
        srgb = ImageUtils.LabTosRGBConventional(lab)
        print("srgb: ", srgb)
        print("lab: ", ImageUtils.sRGBtodisplayP3(srgb[0]))

    def get_image_path_from_args():
        import argparse
        parser = argparse.ArgumentParser(description='Image for processing')
        parser.add_argument('--image', required=True, metavar="path to image file")
        args = parser.parse_args()
        return args.image


if __name__ == "__main__":
    # ImageUtils.save_skin_spectra_uv()
    # ImageUtils.plot_skin_spectra()
    # print (ImageUtils.add_gamma_correction(np.array([0.5, 0.5, 0.5])))
    # print (ImageUtils.add_gamma_correction(ImageUtils.remove_gamma_correction(ImageUtils.CCT_to_sRGB(5837).astype(np.float))*0.5*1.029))
    # print ("CCT_to_sRGB: ", ImageUtils.CCT_to_sRGB(4900))
    # print ("sRGB to CCT: ", ImageUtils.sRGB_to_CCT(ImageUtils.color("#FDDCD2")))
    # print ("CCT: ", ImageUtils.cct(ImageUtils.color("#FDDCD2")))
    # print ("Temp_to_sRGB: ", ImageUtils.Temp_to_sRGB(5366.38))
    # print (ImageUtils.CCT_to_sRGB(5366))
    # print (ImageUtils.compute_luminance(ImageUtils.color("#BCBCBC")))
    # ImageUtils.chromatic_adaptation("/Users/addarsh/Desktop/anastasia-me/IMG_6261.png", ImageUtils.color("#FFF2CF"))
    # ImageUtils.chromatic_adaptation("server/data/new/IMG_1001.png", ImageUtils.color("#FFF1E5"))
    # ImageUtils.chromatic_adaptation("server/data/red/red.png", ImageUtils.color("#FFEBDA"))
    # ImageUtils.chromatic_adaptation("/Users/addarsh/Desktop/anastasia-me/IMG_9872.png", ImageUtils.Temp_to_sRGB(5284))
    # print ("delta: ", ImageUtils.delta_cie2000(ImageUtils.HEX2RGB("#d1af9b"), ImageUtils.HEX2RGB("#daa894")))
    # img = mpimg.imread("/Users/addarsh/Desktop/anastasia-me/IMG_6613.png")
    #ImageUtils.print_lab_to_rgb([60.0, 0.0, 0.0])
    im_path = ImageUtils.get_image_path_from_args()
    image = ImageUtils.read_rgb_image(im_path)

    gray, _, _, _ = ImageUtils.read(im_path)
    #ImageUtils.show_gray(im_path)
    ImageUtils.show(image)
    #print("val: ", ImageUtils.displayP3tosRGB([204.0, 158.0, 141.0]))
    # ImageUtils.show_image("/Users/addarsh/Desktop/anastasia-me/10_24_21_addarsh_foundation/IMG_7819.png")
    # ImageUtils.show_image("/Users/addarsh/Desktop/anastasia-me/sephora_foundation_chart.png")
    #mask = ImageUtils.get_boolean_mask(ImageUtils.read_grayscale_image(
    #    "/Users/addarsh/virtualenvs/facemagik_server/facetone/test_mouth_mask.png"))
    #img = ImageUtils.plot_points_new(ImageUtils.read_rgb_image(
    #    "/Users/addarsh/virtualenvs/facemagik_server/facetone/test_ios.png"), [[692,384]])

    """
    # Testing face contours from client.
    img = ImageUtils.read_rgb_image("/Users/addarsh/virtualenvs/facemagik_server/facetone/test_ios.png")
    with open("/Users/addarsh/virtualenvs/facemagik_server/facetone/face_till_nose_end_contour_points.txt", "r") as f:
        face_till_nose_end_cpts = np.array(json.loads(f.read()))
    with open("/Users/addarsh/virtualenvs/facemagik_server/facetone/right_eye_contour_points.txt", "r") as f:
        right_eye_cpts = np.array(json.loads(f.read()))
    with open("/Users/addarsh/virtualenvs/facemagik_server/facetone/left_eye_contour_points.txt", "r") as f:
        left_eye_cpts = np.array(json.loads(f.read()))
    with open("/Users/addarsh/virtualenvs/facemagik_server/facetone/left_eyebrow_contour_points.txt", "r") as f:
        left_eyebrow_cpts = np.array(json.loads(f.read()))
    with open("/Users/addarsh/virtualenvs/facemagik_server/facetone/right_eyebrow_contour_points.txt", "r") as f:
        right_eyebrow_cpts = np.array(json.loads(f.read()))
    with open("/Users/addarsh/virtualenvs/facemagik_server/facetone/mouth_without_lips_contour_points.txt", "r") as f:
        mouth_cpts = np.array(json.loads(f.read()))
    mask = ImageUtils.get_face_mask_till_nose_end(img.shape, face_till_nose_end_cpts,
                                                  left_eye_cpts, right_eye_cpts,
                                                  left_eyebrow_cpts, right_eyebrow_cpts)
    #mask = ImageUtils.get_mask_from_contour_points(img.shape, mouth_cpts)
    img[mask] = [255, 0, 0]
    ImageUtils.show(img)
    """

    #carr = [62, 0, 0]
    #carr = [73, 0, 0]
    #carr = [50, 0, 0]
    #carr = [38,0,0]
    #carr = [95,-6,95]
    #carr = [69, -43, 50]
    #srgb = ImageUtils.LabTosRGBConventional(np.array(carr))[0].astype(np.float)
    #print("srgb : ", srgb)
    #print("display p3: ", ImageUtils.sRGBtoGray(srgb))

    # print ("munsell: ", ImageUtils.sRGBtoMunsell(ImageUtils.HEX2RGB("#9F796A")))
    # print ("ycrcb: ", ImageUtils.RGB2HEX(ImageUtils.YCrCbtosRGB(ImageUtils.HEX2RGB("#B69C68"))[0]))
    # ImageUtils.chromatic_adaptation("/Users/addarsh/Desktop/anastasia-me/f0.png", ImageUtils.color("#FFF0E6"))
    print ("delta: ", ImageUtils.delta_cie2000(ImageUtils.HEX2RGB("#563521"), ImageUtils.HEX2RGB("#805947")))
    print("delta v2: ", ImageUtils.delta_cie2000_v2(ImageUtils.HEX2RGB("#563521"), ImageUtils.HEX2RGB("#805947")))
    # print ("ycbcr: ", ImageUtils.sRGBtoYCbCr(ImageUtils.HEX2RGB("#cf9d85")))
    # print ("delta 1: ", ImageUtils.delta_cie2000(ImageUtils.color("#9A755E"), ImageUtils.color("#FFEBDA")))
    # print ("delta 2: ", ImageUtils.delta_cie2000(ImageUtils.color("#9A755E"), ImageUtils.color("#FFF1E5")))
    # print ("deltas matrix: ", ImageUtils.delta_e_cie2000_matrix(np.array([[52.2883, 11.285, 18.2971],
    # [94.2010, 4.0615, 10.6879], [95.9256, 2.728, 7.4665]])))
    # ImageUtils.chromatic_adaptation("test/ancha_3.JPG", ImageUtils.color("#e5e2ce"))
    # ImageUtils.chromatic_adaptation("test/IMG_5862.JPG", ImageUtils.color("#e9e4dc"))
    # ImageUtils.show_gray("/Users/addarsh/Desktop/ancha.png")
    # ImageUtils.show_image("test/IMG_5862.JPG")
    # ImageUtils.plot_foundation_depth("#e19094","#daa48a")
    # ImageUtils.plot_foundation_depth("#e19094","#eabea1")
    # ImageUtils.plot_foundation_depth("#e19094","#d9b28b")
    # ImageUtils.plot_foundation_depth("#E2B9A7","#e3bca4")
    # ImageUtils.white_balance(ImageUtils.color("#F1DCC1"))
    # ImageUtils.plot_reflectance(["#E4C9AD", "#C39B82", "#CDA18B", "#ECC5B5"])
    # ImageUtils.plot_reflectance(["#946E59", "#E4CCB2", "#E9C8B3", "#FDF0E4", "#5F3E35"])
    # print ("Mixed color: ", ImageUtils.RGB2HEX(ImageUtils.geometric_mean_mixing("#D0B9C1", "#DAC4BC", 0.8)))
