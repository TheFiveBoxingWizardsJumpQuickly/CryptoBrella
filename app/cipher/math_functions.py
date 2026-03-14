# Prime factorization
from .prime_number import prime_numbers


def make_primenumber():
    f = open('prime_number.py', 'w')
    txt = 'primes =['

    limit = 1000000
    max = int(limit**0.5)
    seachList = [i for i in range(2, limit+1)]
    primeNum = []
    while seachList[0] <= max:
        primeNum.append(seachList[0])
        tmp = seachList[0]
        seachList = [i for i in seachList if i % tmp != 0]
    primeNum.extend(seachList)

    txt += ','.join(map(str, primeNum))

    txt += ']'
    f.write(txt)
    f.close


def calc(n):
    f = ''
    factor_exp_list = []
    primes = prime_numbers()
    p_max = primes[len(primes)-1]

    if n < 0:
        f = '-1 * '
        n *= -1

    for i in range(len(primes)):
        p = primes[i]

        if p**2 > n:
            factor_exp_list.append([n, 1])
            break

        k = 0
        while n % p == 0:
            k += 1
            n //= p

        if k > 0:
            factor_exp_list.append([p, k])

        if n == 1:
            break

        if p == p_max:
            factor_exp_list.append([n, 1])
            break

    notation = ''
    if n > p_max ** 2:
        notation = ' #' + \
            str(n) + ' might have a factor lager than ' + str(p_max)
    elif len(factor_exp_list) == 1 and factor_exp_list[0][1] == 1 and f == '':
        notation = ' (prime)'

    for i in range(len(factor_exp_list)):
        if i > 0:
            f += ' * '

        if factor_exp_list[i][1] == 1:
            f += str(factor_exp_list[i][0])
        else:
            f += str(factor_exp_list[i][0]) + '^' + str(factor_exp_list[i][1])

    return f, notation


def factorize(num):
    n = int(num)
    if n == 0:
        return '0 = 0', ''
    elif n == 1:
        return '1 = 1', ''
    elif n == -1:
        return '-1 = -1', ''
    else:
        factor, notation = calc(n)
        return str(n) + ' = ' + factor, notation


# https://tex2e.github.io/blog/crypto/modular-mul-inverse
def xgcd(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b != 0:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    return a, x0, y0


def modinv(a, m):
    g, x, y = xgcd(a, m)
    if g != 1:
        return 0
    else:
        return x % m

# Debug
'''
if __name__ ==  '__main__':
    #make_primenumber()
    print( factorize('2'))
'''
