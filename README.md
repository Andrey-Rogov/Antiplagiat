# Antiplagiat
This is simple antiplagiat application for comparing Python scripts on their simmilarity.
In my implementation, I used AST module to build a tree from any Python code. Each node in such tree has its own name and children.

The comparison of two scripts runs node-by-node, using Levenstein distance. This comparison runs twice and then combined in one formula, first - for initial arrangement of nodes, second - for sorted nodes (sorting is done by the name of each node, which is string).
This trick helps us to detect such things as replacing function definitions. If functions in both scripts are equal but mixed, comparing them node-by-node in initial positions gives us the simmilarity near 0. Thanks to names of each node (which will be simmilar in both trees, if functions are equal), all nodes in both trees will be sorted simmilarly.
