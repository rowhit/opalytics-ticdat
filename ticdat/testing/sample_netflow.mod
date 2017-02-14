include "sample_netflow_schema.mod";

tuple edgeType {
	string start;
	string end;
}

{edgeType} edges = {<s,e> | <s,e,c> in arcs};
float edgeCapacity[edges] = [<s,e> : c | <s,e,c> in arcs];

dvar float+ edgeFlow[e in edges][commodities] in 0..edgeCapacity[e];

minimize
  sum(<com,start,end,flowCost> in cost) flowCost * edgeFlow[<start,end>][com];
  
subject to {

  //for each inflow, ensure the flow demands are met
  forall (<com,node,qty> in inflow)
    - sum(<start,node> in edges) edgeFlow[<start,node>][com] 
    + sum(<node,end> in edges) edgeFlow[<node,end>][com] == qty;
    
  //for each edge, ensure the flow of all commodities is less than or equal to the capacity
  forall (<start,end> in edges)
    sum(com in commodities) edgeFlow[<start,end>][com] <= edgeCapacity[<start,end>];

}
tuple resultType {
  string start;
  string end;
  string commodity;
  float flow;
}
{resultType} results = {<start,end,com,edgeFlow[<start,end>][com]> | 
  <start,end> in edges,com in commodities};
execute {
  writeln("flow="+results);
}  
