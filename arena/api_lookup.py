"""Compact discovery and batched name lookup in the session's frozen API catalog."""
from .core import ArenaError

GUIDE='LeekScript 4 only. f[integer] => integer means f(argument). Types ending in ? are nullable. Separate overloads determine argument count. Use queries to group related lookups into one tool step; mode=index lists names without definitions.'


def lookup(catalog, arguments):
    mode=arguments.get('mode','search');kind=arguments.get('kind','all')
    if mode not in {'search','index'} or kind not in {'all','functions','constants'}:
        raise ArenaError('mode must be search or index; kind must be all, functions or constants')
    if 'query' in arguments and 'queries' in arguments:
        raise ArenaError('Use query or queries, not both')
    offset=arguments.get('offset',0);limit=arguments.get('limit',500 if mode=='index' else 20)
    maximum=500 if mode=='index' else 50
    if type(offset) is not int or offset<0: raise ArenaError('offset must be a nonnegative integer')
    if type(limit) is not int or not 1<=limit<=maximum:
        raise ArenaError('limit must be 1..'+str(maximum)+' for '+mode)
    kinds=('functions','constants') if kind=='all' else (kind,)
    rows=[(category,name,value) for category in kinds for name,value in sorted(catalog[category].items())]

    def query_text(value, allow_empty=False):
        if not isinstance(value,str) or len(value)>200: raise ArenaError('Each query must be a name or name fragment, maximum 200 characters')
        value=value.strip().removesuffix('()')
        if not value and not allow_empty: raise ArenaError('query must be a nonempty function name or name fragment; use mode=index to list names')
        return value

    def page(matches, continuation):
        end=min(offset+limit,len(matches));next_offset=end if end<len(matches) else None
        return matches[offset:end],{'matches':len(matches),'offset':offset,'returned':len(matches[offset:end]),'next_offset':next_offset,
            'continuation':{'tool':'lookup_api','arguments':{**continuation,'offset':next_offset,'limit':limit}} if next_offset is not None else None}

    if mode=='index':
        if 'queries' in arguments: raise ArenaError('mode=index accepts an optional query fragment, not queries')
        query=query_text(arguments.get('query',''),True)
        matches=[row for row in rows if query.casefold() in row[1].casefold()]
        selected,result=page(matches,{'mode':'index','kind':kind,**({'query':query} if query else {})})
        result.update({category:[name for category2,name,_ in selected if category2==category] for category in kinds})
        result['guide']='Names only. Fetch signatures together with queries=[name1,name2,...]. Index pagination counts catalog entries, not characters.'
        return result

    def search(query):
        matches=[row for row in rows if query.casefold() in row[1].casefold()]
        exact=[row for row in matches if row[1].casefold()==query.casefold()]
        selected,result=page(exact or matches,{'query':query,'kind':kind})
        result.update(query=query,results=[{'kind':category,'name':name,'definition':value} for category,name,value in selected])
        if result['next_offset'] is not None: result['hint']='More matches are available; follow continuation or narrow this query.'
        if query.casefold()=='getleek': result['hint']='getLeek() was removed after version 3. Use getEntity() for your runtime ID; getLeekID() returns the persistent website ID.'
        if not result['matches']: result['hint']='No name matches. Try a shorter fragment or mode=index. Group separate names using queries, not a space-separated query.'
        return result

    if 'queries' in arguments:
        queries=arguments['queries']
        if not isinstance(queries,list) or not 1<=len(queries)<=20: raise ArenaError('queries must contain 1..20 names or fragments')
        normalized=[query_text(query) for query in queries]
        return {'queries':[search(query) for query in normalized],'guide':GUIDE,'tool_steps':1}
    return {**search(query_text(arguments.get('query'))),'guide':GUIDE}
