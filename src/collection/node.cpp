// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/filename.h>

#include "node.h"
#include "dir.h"
#include "collection.h"


// Constructor
Node::Node() :
    m_parent(NULL),
    m_collection(NULL)
{
}

// Destructor
Node::~Node()
{
    if(m_parent)
        m_parent->RemoveChild(this, false);
}

// Get full name of the node if it were under a certain parent or had a certain name
wxString Node::GetFullName(Directory* parent, const wxString& newname)
{
    if(parent == NULL)
        parent = m_parent;

    if(parent == NULL)
        return wxEmptyString;

    wxChar pathSep = wxFileName::GetPathSeparator();
    if(newname == wxEmptyString)
    {
        return parent->GetFullName() + pathSep + m_name;
    }
    else
    {
        return parent->GetFullName() + pathSep + newname;
    }
}

// Can the node be moved
bool Node::CanMove(Directory* parent)
{
    return (m_parent != parent);
}

// Move this node
bool Node::Move(Directory* parent)
{
    if(!CanMove(parent))
        return false;

    if(m_parent)
        m_parent->RemoveChild(this, false);

    if(parent)
        parent->AddChild(this);

    return true;
}

// Can the node be deleted
bool Node::CanDelete()
{
    return true;
}

// Delete the node
bool Node::Delete()
{
    if(!CanDelete())
        return false;

    delete this;
    return true;
}

// Can the node be renamed
bool Node::CanRename(const wxString& name)
{
    if(name == wxT(".") || name == wxT(".."))
        return false;

    if(name.Find(wxT('/')) != wxNOT_FOUND || name.Find(wxT('\\')) != wxNOT_FOUND)
        return false;

    return (name != m_name);
}

// Rename the node
bool Node::Rename(const wxString& name)
{
    if(!CanRename(name))
        return false;

    if(m_name != name)
    {
        m_name = name;
        if(m_collection)
            m_collection->SetDirty();

        Reset();
    }

    return true;
}

// Reset cache information
void Node::Reset()
{
    m_collection = NULL;
    m_fullname.Clear();
    m_fullpath.Clear();

    if(m_parent)
    {
        m_collection = m_parent->m_collection;
        if(m_collection)
        {
            wxChar pathSep = wxFileName::GetPathSeparator();

            // Full name (top level collection name is empty)
            m_fullname = m_parent->GetFullName() + pathSep + m_name;

            // Full path (make sure not to double separators)
            m_fullpath = m_parent->GetFullPath();
            if(m_fullpath.Last() != pathSep)
                m_fullpath = m_fullpath + pathSep;
            m_fullpath = m_fullpath + m_name;
        }
    }
}




