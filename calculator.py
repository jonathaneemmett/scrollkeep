# basic import 
import math

from mcp.server.fastmcp import FastMCP

# instantiate an MCP server client
mcp = FastMCP("Hello world")

# TOOLS

# addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# subtraction tool
@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract one number from another."""
    return a - b

# multiplication tool
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together."""
    return a * b

# division tool
@mcp.tool()
def divide(a: int, b: int) -> float:
    """Divide one number by another."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

# square root tool
@mcp.tool()
def square_root(a: int) -> float:
    """Calculate the square root of a number."""
    if a < 0:
        raise ValueError("Cannot calculate the square root of a negative number.")
    return math.sqrt(a)

# cube root tool
@mcp.tool()
def cube_root(a: int) -> float:
    """Calculate the cube root of a number."""
    return math.cbrt(a)

# factorial tool
@mcp.tool()
def factorial(n: int) -> int:
    """Calculate the factorial of a number."""
    if n < 0:
        raise ValueError("Cannot calculate the factorial of a negative number.")
    return math.factorial(n)

# log tool
@mcp.tool()
def log(a: int, base: int = math.e) -> float:
    """Calculate the logarithm of a number to a given base."""
    if a <= 0:
        raise ValueError("Cannot calculate the logarithm of a non-positive number.")
    if base <= 1:
        raise ValueError("Base must be greater than 1.")
    return math.log(a, base)

# remainder tool
@mcp.tool()
def remainder(a: int, b: int) -> int:
    """Calculate the remainder of a division operation."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a % b

# sin tool
@mcp.tool()
def sin(a: int) -> float:
    """Calculate the sine of an angle in degrees."""
    return math.sin(math.radians(a))    

# cos tool
@mcp.tool()
def cos(a: int) -> float:
    """Calculate the cosine of an angle in degrees."""
    return math.cos(math.radians(a))    

# tan tool
@mcp.tool()
def tan(a: int) -> float:
    """tan of a number"""
    return float(math.tan(a))

# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# execute and return the stdio output
if __name__ == "__main__":
    mcp.run(transport="stdio")