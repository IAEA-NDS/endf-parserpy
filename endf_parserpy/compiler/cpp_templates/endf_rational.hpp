#ifndef CPP_ENDF_RATIONAL_HPP
#define CPP_ENDF_RATIONAL_HPP


#include <climits>
#include <cstdlib>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string>


// Exact rational number for the arithmetic of ENDF recipe expressions.
//
// Expressions in ENDF recipes are evaluated exactly: a division of two
// integers gives a fraction (e.g. 13/6), and only where an integer is
// needed (an integer field, a loop bound, an index) must the result be
// an integer. The Python parser uses fractions.Fraction for the same
// purpose (see endf_parserpy.interpreter.endf_mapping_utils).
//
// - The constructor is explicit and arithmetic with int and double is
//   provided by dedicated overloads, so that no ambiguous implicit
//   conversions arise. Arithmetic with a double gives a double.
// - The only implicit conversion is to int; it throws if the value is
//   not an integer. Integer contexts are therefore checked automatically.
// - The conversion to double is explicit.

class EndfRational {
public:
    explicit EndfRational(long long num = 0, long long den = 1) {
        if (den == 0) {
            throw std::runtime_error("division by zero in expression");
        }
        if (den < 0) {
            num = -num;
            den = -den;
        }
        long long g = gcd(num < 0 ? -num : num, den);
        _num = num / g;
        _den = den / g;
    }

    long long numerator() const { return _num; }
    long long denominator() const { return _den; }
    bool is_integer() const { return _den == 1; }

    explicit operator double() const {
        return static_cast<double>(_num) / static_cast<double>(_den);
    }

    operator int() const {
        if (_den != 1) {
            throw std::runtime_error(
                "the value " + to_string() + " is not an integer");
        }
        if (_num > INT_MAX || _num < INT_MIN) {
            throw std::runtime_error(
                "the value " + to_string() + " exceeds the range of an integer");
        }
        return static_cast<int>(_num);
    }

    std::string to_string() const {
        std::ostringstream oss;
        oss << _num;
        if (_den != 1) oss << "/" << _den;
        return oss.str();
    }

    static long long checked_mul(long long a, long long b) {
        if (a != 0 && b != 0) {
            long long abs_a = a < 0 ? -a : a;
            long long abs_b = b < 0 ? -b : b;
            if (abs_a > LLONG_MAX / abs_b) {
                throw std::runtime_error("integer overflow in expression");
            }
        }
        return a * b;
    }

    static long long checked_add(long long a, long long b) {
        if ((b > 0 && a > LLONG_MAX - b) || (b < 0 && a < LLONG_MIN - b)) {
            throw std::runtime_error("integer overflow in expression");
        }
        return a + b;
    }

private:
    static long long gcd(long long a, long long b) {
        while (b != 0) {
            long long t = a % b;
            a = b;
            b = t;
        }
        return a == 0 ? 1 : a;
    }

    long long _num;
    long long _den;
};


inline EndfRational operator-(const EndfRational& x) {
    return EndfRational(-x.numerator(), x.denominator());
}

inline EndfRational operator+(const EndfRational& x, const EndfRational& y) {
    return EndfRational(
        EndfRational::checked_add(
            EndfRational::checked_mul(x.numerator(), y.denominator()),
            EndfRational::checked_mul(y.numerator(), x.denominator())),
        EndfRational::checked_mul(x.denominator(), y.denominator()));
}

inline EndfRational operator-(const EndfRational& x, const EndfRational& y) {
    return x + (-y);
}

inline EndfRational operator*(const EndfRational& x, const EndfRational& y) {
    return EndfRational(
        EndfRational::checked_mul(x.numerator(), y.numerator()),
        EndfRational::checked_mul(x.denominator(), y.denominator()));
}

inline EndfRational operator/(const EndfRational& x, const EndfRational& y) {
    if (y.numerator() == 0) {
        throw std::runtime_error("division by zero in expression");
    }
    return EndfRational(
        EndfRational::checked_mul(x.numerator(), y.denominator()),
        EndfRational::checked_mul(x.denominator(), y.numerator()));
}


// mixed arithmetic with int (exact) and double (inexact)
#define ENDF_RATIONAL_MIXED_OPS(OP) \
inline EndfRational operator OP(const EndfRational& x, int y) { return x OP EndfRational(y); } \
inline EndfRational operator OP(int x, const EndfRational& y) { return EndfRational(x) OP y; } \
inline double operator OP(const EndfRational& x, double y) { return static_cast<double>(x) OP y; } \
inline double operator OP(double x, const EndfRational& y) { return x OP static_cast<double>(y); }

ENDF_RATIONAL_MIXED_OPS(+)
ENDF_RATIONAL_MIXED_OPS(-)
ENDF_RATIONAL_MIXED_OPS(*)
ENDF_RATIONAL_MIXED_OPS(/)
#undef ENDF_RATIONAL_MIXED_OPS


inline int endf_rational_compare(const EndfRational& x, const EndfRational& y) {
    // the denominators are positive
    long long lhs = EndfRational::checked_mul(x.numerator(), y.denominator());
    long long rhs = EndfRational::checked_mul(y.numerator(), x.denominator());
    return (lhs > rhs) - (lhs < rhs);
}


// comparisons: exact with int, via double with double
#define ENDF_RATIONAL_COMPARISON(OP) \
inline bool operator OP(const EndfRational& x, const EndfRational& y) { return endf_rational_compare(x, y) OP 0; } \
inline bool operator OP(const EndfRational& x, int y) { return endf_rational_compare(x, EndfRational(y)) OP 0; } \
inline bool operator OP(int x, const EndfRational& y) { return endf_rational_compare(EndfRational(x), y) OP 0; } \
inline bool operator OP(const EndfRational& x, double y) { return static_cast<double>(x) OP y; } \
inline bool operator OP(double x, const EndfRational& y) { return x OP static_cast<double>(y); }

ENDF_RATIONAL_COMPARISON(==)
ENDF_RATIONAL_COMPARISON(!=)
ENDF_RATIONAL_COMPARISON(<)
ENDF_RATIONAL_COMPARISON(<=)
ENDF_RATIONAL_COMPARISON(>)
ENDF_RATIONAL_COMPARISON(>=)
#undef ENDF_RATIONAL_COMPARISON


inline std::ostream& operator<<(std::ostream& os, const EndfRational& x) {
    os << x.to_string();
    return os;
}


#endif
