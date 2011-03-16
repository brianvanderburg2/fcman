// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/arrstr.h>

#include "version.h"


// Constructor
Version::Version()
{
}

// Destructor
Version::~Version()
{
}

// Set the version string and parts
void Version::Set(const wxString& version)
{
    wxString part;
    int type = 0; // 0 = none, 1 = digits, 2 = letters

    m_parts.Clear();
    for(size_t pos = 0, count = version.Len(); pos < count; pos++)
    {
        if(version[pos] >= wxT('0') && version[pos] <= wxT('9'))
        {
            if(type != 1 && part.Len() > 0)
            {
                m_parts.Add(PartValue(part));
                part.Clear();
            }
            type = 1;
            part = part + version[pos];
        }
        else if((version[pos] >= wxT('a') && version[pos] <= wxT('z')) ||
                (version[pos] >= wxT('A') && version[pos] <= wxT('Z')))
        {
            if(type != 2 && part.Len() > 0)
            {
                m_parts.Add(PartValue(part));
                part.Clear();
            }
            type = 2;
            part = part + version[pos];
        }
        else
        {
            if(type != 0 && part.Len() > 0)
            {
                m_parts.Add(PartValue(part));
                part.Clear();
            }
            type = 0;
        }
    }

    if(type != 0 && part.Len() > 0)
        m_parts.Add(PartValue(part));

    if(m_parts.Count() > 0)
        m_version = version;
    else
        m_version.Clear();
}

// Compare to another version object
int Version::Compare(const Version& other) const
{
    size_t lp1 = m_parts.Count();
    size_t lp2 = other.m_parts.Count();
    size_t max = lp1;
    if(lp2 > max)
        max = lp2;

    for(size_t pos = 0; pos < max; pos++)
    {
        int part1 = 0;
        if(pos < lp1)
            part1 = m_parts[pos];

        int part2 = 0;
        if(pos < lp2)
            part2 = other.m_parts[pos];

        int result = part1 - part2;
        if(result != 0)
            return result;
    }

    return 0;
}

// Get the value of a part
static const wxChar* _pre[] = { wxT("alpha"), wxT("beta"), wxT("pre"), wxT("rc") };
static const wxChar* _post[] = { wxT("a"), wxT("b"), wxT("c"), wxT("d"), wxT("e"), wxT("f"),
                                 wxT("g"), wxT("h"), wxT("i"), wxT("j"), wxT("k"), wxT("l"),
                                 wxT("m"), wxT("n"), wxT("o"), wxT("p"), wxT("q"), wxT("r"),
                                 wxT("s"), wxT("t"), wxT("u"), wxT("v"), wxT("w"), wxT("x"),
                                 wxT("y"), wxT("z"), wxT("final") };

int Version::PartValue(const wxString& part)
{
    const wxArrayString pre(sizeof(_pre) / sizeof(_pre[0]), _pre);
    const wxArrayString post(sizeof(_post) / sizeof(_post[0]), _post);

    int index;

    // Pre-0 parts
    index = pre.Index(part);
    if(index != wxNOT_FOUND)
    {
        return index - static_cast<int>(pre.Count());
    }

    // Post-0 but Pre-1
    index = post.Index(part);
    if(index != wxNOT_FOUND)
    {
        return index + 1;
    }

    // Number value
    long n = 0;
    if(!part.ToLong(&n))
        return 0;

    // If less or equal to zero, return 0, (it is not ever really less than
    // since a '-' would cause a split in a part, but test it in case)
    if(n <= 0)
        return 0;

    // If greater than 0, adjust by post size (since post is less than '1')
    return static_cast<int>(n) + static_cast<int>(post.Count());
}

// Is this a valid version object
bool Version::IsOk() const
{
    return m_parts.Count() > 0;
}


