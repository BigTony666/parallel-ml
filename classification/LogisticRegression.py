# -*- coding: utf-8 -*-
import numpy as np
import argparse
from time import time
from SparseVector import SparseVector
import json

"""
Parameter example: 
  --testdata "mushrooms/mushrooms.test" --beta "beta" --lam 0.2 --max_iter 20 --eps 0.1 mushrooms/mushrooms.train
  --testdata "newsgroups/news.test" --beta "beta" --lam 0.0 --max_iter 50 --eps 0.1 --plot newsgroups/news.train
"""


def readBeta(input):
    """ Read a vector β from file input. Each line of input contains pairs of the form:
                (feature,value)
        The return value is β represented as a sparse vector.
    """
    beta = SparseVector({})
    with open(input, 'r') as fh:
        for line in fh:
            (feat, val) = line.strip().strip('()').split(',')
            beta[feat] = float(val)
    return beta


def writeBeta(output, beta):
    """ Write a vector β to a file ouptut.  Each line of output contains pairs of the form:
                (feature,value)
 
    """
    with open(output, 'w') as fh:
        for key in beta:
            fh.write('(%s,%f)\n' % (key, beta[key]))

def writePlot(output, plot_data):
    """
    Serialize the plot_data into JSON format
    :param output:
    :param plot_data:
    :return:
    """
    with open(output, 'w') as fh:
        fh.write(json.dumps(plot_data))


def readData(input_file):
    """  Read data from an input file. Each line of the file contains tuples of the form

                    (x,y)  

         x is a dictionary of the form:                 

           { "feature1": value, "feature2":value, ...}

         and y is a binary value +1 or -1.

         The return value is a list containing tuples of the form
                 (SparseVector(x),y)             

    """
    listSoFar = []
    with open(input_file, 'r') as fh:
        for line in fh:
            (x, y) = eval(line)
            x = SparseVector(x)
            listSoFar.append((x, y))

    return listSoFar


def getAllFeatures(data):
    """ Get all the features present in dataset data. 
	The input is:
            - data: a python list containing pairs of the form (x,y), where x is a sparse vector and y is a binary value

	The output is:
	    - a list containing all features present in all x in data.

    """
    features = SparseVector({})
    for (x, y) in data:
        features = features + x
    return features.keys()


def logisticLoss(beta, x, y):
    """
        Given sparse vector beta, a sparse vector x, and a binary value y in {-1,+1}, compute the logistic loss
               
                l(β;x,y) = log( 1.0 + exp(-y * <β,x>) )

	The input is:
	    - beta: a sparse vector β
	    - x: a sparse vector x
            - y: a binary value in {-1,+1}

    """
    return np.log(1. + np.exp(-y * beta.dot(x)))


def gradLogisticLoss(beta, x, y):
    """
        Given a sparse vector beta, a sparse vector x, and 
        a binary value y in {-1,+1}, compute the gradient of the logistic loss 

              ∇l(B;x,y) = -y / (1.0 + exp(y <β,x> )) * x

	The input is:
	    - beta: a sparse vector β
	    - x: a sparse vector x
            - y: a binary value in {-1,+1}


    """
    return -y / (1. + np.exp(y * beta.dot(x))) * x


def totalLoss(data, beta, lam=0.0):
    """  Given a sparse vector beta and a dataset  compute the regularized total logistic loss :
              
               L(β) = Σ_{(x,y) in data}  l(β;x,y)  + λ ||β ||_2^2             
        
         Inputs are:
            - data: a python list containing pairs of the form (x,y), where x is a sparse vector and y is a binary value
            - beta: a sparse vector β
            - lam: the regularization parameter λ
    """
    loss = 0.0
    for (x, y) in data:
        loss += logisticLoss(beta, x, y)
    return loss + lam * beta.dot(beta)


def gradTotalLoss(data, beta, lam=0.0):
    """  Given a sparse vector beta and a dataset perform compute the gradient of regularized total logistic loss :
            
              ∇L(β) = Σ_{(x,y) in data}  ∇l(β;x,y)  + 2λ β   
        
         Inputs are:
            - data: a python list containing pairs of the form (x,y), where x is a sparse vector and y is a binary value
            - beta: a sparse vector β
            - lam: the regularization parameter λ
    """
    grad_loss = SparseVector()
    for (x, y) in data:
        grad_loss += gradLogisticLoss(beta, x, y)
    return grad_loss + 2 * lam * beta

def lineSearch(fun, x, grad, fx, gradNormSq, a=0.2, b=0.6):
    """ Given function fun, a current argument x, and gradient grad=∇fun(x), 
        perform backtracking line search to find the next point to move to.
        (see Boyd and Vandenberghe, page 464).

        Both x and grad are presumed to be SparseVectors.
	
        Inputs are:
	    - fun: the objective function f.
	    - x: the present input (a Sparse Vector)
            - grad: the present gradient (as Sparse Vector)
            - fx: precomputed f(x) 
            - grad: precomputed ∇f(x)
            - Optional parameters a,b  are the parameters of the line search.

        Given function fun, and current argument x, and gradient grad=∇fun(x), the function finds a t such that
        fun(x - t * ∇f(x)) <= f(x) - a * t * <∇f(x),∇f(x)>

        The return value is the resulting value of t.
    """
    t = 1.0
    while fun(x - t * grad) > fx - a * t * gradNormSq:
        t = b * t
    return t


def test(data, beta):
    """ Output the quantities necessary to compute the accuracy, precision, and recall of the prediction of labels in a dataset under a given β.
        
        The accuracy (ACC), precision (PRE), and recall (REC) are defined in terms of the following sets:

                 P = datapoints (x,y) in data for which <β,x> > 0
                 N = datapoints (x,y) in data for which <β,x> <= 0
                 
                 TP = datapoints in (x,y) in P for which y=+1  
                 FP = datapoints in (x,y) in P for which y=-1  
                 TN = datapoints in (x,y) in N for which y=-1
                 FN = datapoints in (x,y) in N for which y=+1

        For #XXX the number of elements in set XXX, the accuracy, precision, and recall of parameter vector β over data are defined as:
         
                 ACC(β,data) = ( #TP+#TN ) / (#P + #N)
                 PRE(β,data) = #TP / (#TP + #FP)
                 REC(β,data) = #TP/ (#TP + #FN)

        Inputs are:
             - data: an RDD containing pairs of the form (x,y)
             - beta: vector β

        The return values are
             - ACC, PRE, REC
       
    """
    P = N = TP = FP = TN = FN = 0
    for (x, y) in data:
        if beta.dot(x) > 0:
            P += 1
            if y == 1:
                TP += 1
            else:
                FP += 1
        else:
            N += 1
            if y == -1:
                TN += 1
            else:
                FN += 1

    ACC = 1. * (TP + TN) / (P + N)
    PRE = 1. * TP / (TP + FP)
    REC = 1. * TP / (TP + FN)
    return ACC, PRE, REC


def train(data, beta_0, lam, max_iter, eps, test_data=None, plot_data=None):
    k = 0
    gradNorm = 2 * eps
    beta = beta_0
    start = time()
    while k < max_iter and gradNorm > eps:
        obj = totalLoss(data, beta, lam)

        grad = gradTotalLoss(data, beta, lam)
        gradNormSq = grad.dot(grad)
        gradNorm = np.sqrt(gradNormSq)

        fun = lambda x: totalLoss(data, x, lam)
        gamma = lineSearch(fun, beta, grad, obj, gradNormSq)

        beta = beta - gamma * grad
        if test_data == None:
            print 'k = ', k, '\tt = ', time() - start, '\tL(β_k) = ', obj, '\t||∇L(β_k)||_2 = ', gradNorm, '\tgamma = ', gamma
        else:
            acc, pre, rec = test(test_data, beta)
            end = time() - start
            if plot_data is not None:
                plot_data['period'].append(end)
                plot_data['gradNorm'].append(gradNorm)
                plot_data['acc'].append(acc)
                plot_data['pre'].append(pre)
                plot_data['rec'].append(rec)
            print 'k = ', k, '\tt = ', end, '\tL(β_k) = ', obj, '\t||∇L(β_k)||_2 = ', gradNorm, '\tgamma = ', gamma, '\tACC = ', acc, '\tPRE = ', pre, '\tREC = ', rec
        k = k + 1

    return beta, gradNorm, k

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Logistic Regression.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('traindata', default=None,
                        help='Input file containing (x,y) pairs, used to train a logistic model')
    parser.add_argument('--testdata', default=None,
                        help='Input file containing (x,y) pairs, used to test a logistic model')
    parser.add_argument('--beta', default='beta',
                        help='File where beta is stored (when training) and read from (when testing)')
    parser.add_argument('--lam', type=float, default=0.0, help='Regularization parameter λ')
    parser.add_argument('--max_iter', type=int, default=100, help='Maximum number of iterations')
    parser.add_argument('--eps', type=float, default=0.1,
                        help='ε-tolerance. If the l2_norm gradient is smaller than ε, gradient descent terminates.')
    parser.add_argument('--plot', default=False,
                        help='Plot the data', action='store_true')

    args = parser.parse_args()

    print 'Reading training data from', args.traindata
    traindata = readData(args.traindata)
    print 'Read', len(traindata), 'data points with', len(getAllFeatures(traindata)), 'features in total'

    if args.testdata is not None:
        print 'Reading test data from', args.testdata
        testdata = readData(args.testdata)
        print 'Read', len(testdata), 'data points with', len(getAllFeatures(testdata)), 'features'
    else:
        testdata = None

    beta0 = SparseVector({})

    print 'Training on data from', args.traindata, 'with λ =', args.lam, ', ε =', args.eps, ', max iter = ', args.max_iter
    if args.plot is not None:
        plot_data = {
            'period': [],
            'gradNorm': [],
            'acc': [],
            'pre': [],
            'rec': []
        }
        beta, gradNorm, k = train(traindata, beta_0=beta0, lam=args.lam, max_iter=args.max_iter, eps=args.eps,
                                  test_data=testdata, plot_data=plot_data)
        writePlot('plot_data_non_parallel.json', plot_data)
        print 'Plot data is saved.'
    else:
        beta, gradNorm, k = train(traindata, beta_0=beta0, lam=args.lam, max_iter=args.max_iter, eps=args.eps,
                                  test_data=testdata)
    print 'Algorithm ran for', k, 'iterations. Converged:', gradNorm < args.eps
    print 'Saving trained β in', args.beta
    writeBeta(args.beta, beta)
