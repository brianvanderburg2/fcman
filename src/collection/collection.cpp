// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/string.h>
#include <wx/filename.h>
#include <wx/filefn.h>
#include <wx/xml/xml.h>

#include "collection.h"


// Destructor
Collection::~Collection()
{
}

// New
Collection* Collection::New(const wxString& filename)
{
    return new Collection(filename);
}

// Open
Collection* Collection::Open(const wxString& filename)
{
    wxXmlDocument doc;

    // Load the document
    if(!doc.Load(filename))
        return NULL;

    if(doc.GetRoot()->GetName() != wxT("collection"))
        return NULL;

    // Find the contents
    wxXmlNode* child = doc.GetRoot()->GetChildren();
    while(child)
    {
        if(child->GetType() == wxXML_ELEMENT_NODE && child->GetName() == wxT("contents"))
            break;

        child = child->GetNext();
    }

    if(!child)
        return NULL;

    return new Collection(filename, child);
}

// Save
wxXmlNode* Collection::Save()
{
    wxXmlNode* node = new wxXmlNode(NULL, wxXML_ELEMENT_NODE, wxT("contents"));

    NodeList children = GetChildren();
    for(NodeList::iterator it = children.begin(), end = children.end(); it != end; ++it)
    {
        wxXmlNode* child = (*it)->Save();
        node->AddChild(child);
    }

    return node;
}

bool Collection::SaveFile(bool backup)
{
    // Backup if desired
    if(wxFileName::FileExists(m_filename) && backup)
    {
        if(wxFileName::FileExists(m_backup))
        {
            if(!::wxRemoveFile(m_backup))
                return false;
        }

        if(!::wxRenameFile(m_filename, m_backup))
            return false;
    }

    // Save file
    wxXmlNode* contents = Save();
    wxXmlNode* docroot = new wxXmlNode(NULL, wxXML_ELEMENT_NODE, wxT("collection"));
    docroot->AddChild(contents);

    wxXmlDocument doc;
    doc.SetRoot(docroot);

    bool result = doc.Save(m_filename);
    if(result)
        m_dirty = false;

    return result;
}

// Delete
bool Collection::CanDelete()
{
    return false;
}

// Rename
bool Collection::CanRename(const wxString& WXUNUSED(name))
{
    return false;
}

// Move
bool Collection::CanMove(Directory* WXUNUSED(parent))
{
    return false;
}

// Reset only child nodes
void Collection::Reset()
{
    for(NodeList::iterator it = m_children.begin(), end = m_children.end(); it != end; ++it)
    {
        (*it)->Reset();
    }
}

// Close the collection
void Collection::Close()
{
    delete this;
}

// Constructor
Collection::Collection(const wxString& filename, wxXmlNode* node)
{
    // Store some information
    m_collection = this;
    m_name = wxEmptyString;
    m_fullname = wxEmptyString;

    wxFileName fn(filename);
    fn.MakeAbsolute();

    m_fullpath = fn.GetPath();
    m_filename = filename;
    m_backup = filename + wxT(".bak");

    // Load data if available
    if(node)
    {
        wxXmlNode* child = node->GetChildren();
        while(child)
        {
            if(child->GetType() != wxXML_ELEMENT_NODE)
            {
                child = child->GetNext();
                continue;
            }

            if(child->GetName() == wxT("dir"))
            {
                Directory* d = new Directory(child);
                AddChild(d);
            }
            else if(child->GetName() == wxT("file"))
            {
                File* f = new File(child);
                AddChild(f);
            }

            child = child->GetNext();
        }
    }

    // Clear dirty flag for new or opened collection
    m_dirty = false;
}



