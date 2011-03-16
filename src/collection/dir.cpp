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
#include <wx/xml/xml.h>

#include "dir.h"
#include "file.h"
#include "collection.h"


// Constructor
Directory::Directory()
{
}

// Construct from xml
Directory::Directory(wxXmlNode* node)
{
    m_name = node->GetPropVal(wxT("name"), wxT("untitled"));

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
            Directory* dir = new Directory(child);
            AddChild(dir);
        }
        else if(child->GetName() == wxT("file"))
        {
            File* file = new File(child);
            AddChild(file);
        }


        child = child->GetNext();
    }
}

// Destructor
Directory::~Directory()
{
    while(m_children.size() > 0)
    {
        delete m_children.front();
    }
}

// Save the contents of the node
wxXmlNode* Directory::Save()
{
    wxXmlNode* node = new wxXmlNode(NULL, wxXML_ELEMENT_NODE, wxT("dir"));
    node->AddProperty(wxT("name"), m_name);

    NodeList children = GetChildren();
    for(NodeList::iterator it = children.begin(), end = children.end(); it != end; ++it)
    {
        wxXmlNode* child = (*it)->Save();
        node->AddChild(child);
    }

    return node;
}

// Does the item exist
bool Directory::Exists() const
{
    if(!m_collection)
        return false;

    return wxFileName::DirExists(GetFullPath());
}

// Can the directory be moved
bool Directory::CanMove(Directory* parent)
{
    if(parent == this)
        return false;


    DirectoryList children = GetDirectories(true);
    for(DirectoryList::iterator it = children.begin(), end = children.end(); it != end; ++it)
    {
        if(*it == parent)
            return false;
    }

    return Node::CanMove(parent);
}

// Reset cache information
void Directory::Reset()
{
    Node::Reset();

    for(NodeList::iterator it = m_children.begin(), end = m_children.end(); it != end; ++it)
    {
        (*it)->Reset();
    }
}

// Add a node
void Directory::AddChild(Node* node)
{
    if(node->m_parent == this)
        return;

    if(node->m_parent != NULL)
        node->m_parent->RemoveChild(node, false);

    m_children.push_back(node);
    node->m_parent = this;
    node->Reset();

    if(m_collection)
        m_collection->SetDirty();
}

// Remove a node
void Directory::RemoveChild(Node* node, bool reset)
{
    if(node->m_parent != this)
        return;

    m_children.remove(node);
    node->m_parent = NULL;

    if(reset)
        node->Reset();

     if(m_collection)
         m_collection->SetDirty();
}

// Get the children
static bool dir_sort(Node* node1, Node* node2)
{
    const wxString& name1 = node1->GetName();
    const wxString& name2 = node2->GetName();

    return name1.Cmp(name2) < 0;
}

NodeList Directory::GetChildren(bool recursive)
{
    NodeList children(m_children);
    children.sort(dir_sort);

    NodeList results;
    for(NodeList::iterator it = children.begin(), end = children.end(); it != end; ++it)
    {
        results.push_back(*it);

        // Recurse if a directory
        Directory* dir = dynamic_cast<Directory*>(*it);
        if(dir && recursive)
        {
            NodeList subitems = dir->GetChildren(recursive);
            results.insert(results.end(), subitems.begin(), subitems.end());
        }
    }

    return results;
}

// Get directories
DirectoryList Directory::GetDirectories(bool recursive)
{
    NodeList nodes = GetChildren(recursive);
    DirectoryList results;

    for(NodeList::iterator it = nodes.begin(), end=nodes.end(); it != end; ++it)
    {
        Directory* dir = dynamic_cast<Directory*>(*it);
        if(dir)
            results.push_back(dir);
    }

    return results;
}

// Get files
FileList Directory::GetFiles(bool recursive)
{
    NodeList nodes = GetChildren(recursive);
    FileList results;

    for(NodeList::iterator it = nodes.begin(), end=nodes.end(); it != end; ++it)
    {
        File* file = dynamic_cast<File*>(*it);
        if(file)
            results.push_back(file);
    }

    return results;
}

// Are there any directory children
bool Directory::HasDirectories() const
{
    for(NodeList::const_iterator it = m_children.begin(), end = m_children.end(); it != end; ++it)
    {
        Directory* dir = dynamic_cast<Directory*>(*it);
        if(dir)
            return true;
    }
    return false;
}

// Are there any file children
bool Directory::HasFiles() const
{
    for(NodeList::const_iterator it = m_children.begin(), end = m_children.end(); it != end; ++it)
    {
        File* file = dynamic_cast<File*>(*it);
        if(file)
            return true;
    }
    return false;
}

// Does the specified directory exist
bool Directory::HasDirectory(const wxString& name) const
{
    for(NodeList::const_iterator it = m_children.begin(), end = m_children.end(); it != end; ++it)
    {
        Directory* dir = dynamic_cast<Directory*>(*it);
        if(dir && dir->GetName() == name)
            return true;
    }
    return false;
}

// Does the specified file exist
bool Directory::HasFile(const wxString& name) const
{
    for(NodeList::const_iterator it = m_children.begin(), end = m_children.end(); it != end; ++it)
    {
        File* file = dynamic_cast<File*>(*it);
        if(file && file->GetName() == name)
            return true;
    }
    return false;
}


